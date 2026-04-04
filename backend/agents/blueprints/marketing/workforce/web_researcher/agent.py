from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.marketing.workforce.web_researcher.skills import format_skills
from agents.blueprints.marketing.workforce.web_researcher.commands import research_gather, research_analyze

logger = logging.getLogger(__name__)


class WebResearcherBlueprint(WorkforceBlueprint):
    name = "Web Researcher"
    slug = "web_researcher"
    description = "Researches trends, competitors, and content opportunities via web search"
    tags = ["research", "intelligence", "trends"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a web research agent. Search for industry trends, competitor activity, and content opportunities. Return structured findings with URLs, relevance assessment, and suggested angles. Always connect findings to the project goal.

When executing tasks, respond with a JSON object:
{
    "findings": [
        {"title": "...", "url": "...", "relevance": "high|medium|low", "summary": "...", "suggested_angle": "..."}
    ],
    "report": "Summary of research conducted and key takeaways"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    research_gather = research_gather
    research_analyze = research_analyze

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        if task.command_name == "research-analyze":
            return self._execute_analyze(agent, task)
        return self._execute_gather(agent, task)

    def _execute_gather(self, agent: Agent, task: AgentTask) -> str:
        """Phase 1: Search and collect raw findings (Haiku)."""
        from agents.ai.claude_client import call_claude
        from integrations.websearch.service import search

        query = task.exec_summary or ""
        search_results = search(query)

        suffix = f"""Here are the web search results to organize:

<search_results>
{json.dumps(search_results, default=str, indent=2) if search_results else 'No results found.'}
</search_results>

Organize these results. Extract key facts, URLs, and relevance. Return structured JSON:
{{
    "findings": [
        {{"title": "...", "url": "...", "relevance": "high|medium|low", "summary": "...", "raw_data": "..."}}
    ]
}}"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model="claude-haiku-4-5",
            max_tokens=8192,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        # Create the analyze task as a dependent
        from agents.models import AgentTask as TaskModel
        TaskModel.objects.create(
            agent=agent,
            command_name="research-analyze",
            status=TaskModel.Status.AWAITING_DEPENDENCIES,
            blocked_by=task,
            exec_summary=f"Analyze: {task.exec_summary}",
            step_plan="Analyze the gathered research and produce strategic recommendations.",
        )
        logger.info("Created research-analyze task dependent on %s", task.id)

        return response

    def _execute_analyze(self, agent: Agent, task: AgentTask) -> str:
        """Phase 2: Deep analysis of gathered data (Sonnet). Stores results as document."""
        from agents.ai.claude_client import call_claude, parse_json_response
        from projects.models import Document, Tag

        # Read raw findings from the blocker task
        raw_findings = ""
        if task.blocked_by and task.blocked_by.report:
            raw_findings = task.blocked_by.report

        suffix = f"""Here are the raw research findings to analyze:

<raw_research>
{raw_findings or 'No raw findings available.'}
</raw_research>

Analyze these findings in the context of the project goal. Produce strategic recommendations.
Return JSON:
{{
    "findings": [
        {{"title": "...", "url": "...", "relevance": "high|medium|low", "summary": "...", "suggested_angle": "..."}}
    ],
    "report": "Executive summary of the analysis with key takeaways and recommended actions"
}}"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model="claude-sonnet-4-6",
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        data = parse_json_response(response)
        report = data.get("report", response) if data else response

        # Store analysis as a research document
        department = agent.department
        findings = data.get("findings", []) if data else []
        if findings:
            doc_content = f"# Research Analysis: {task.exec_summary}\n\n"
            for f in findings:
                doc_content += f"## {f.get('title', 'Finding')}\n"
                if f.get("url"):
                    doc_content += f"**Source:** {f['url']}\n"
                if f.get("relevance"):
                    doc_content += f"**Relevance:** {f['relevance']}\n"
                doc_content += f"\n{f.get('summary', '')}\n"
                if f.get("suggested_angle"):
                    doc_content += f"\n**Suggested angle:** {f['suggested_angle']}\n"
                doc_content += "\n---\n\n"

            doc = Document.objects.create(
                title=f"Research: {task.exec_summary[:80]}",
                content=doc_content,
                department=department,
                doc_type=Document.DocType.RESEARCH,
            )
            tag, _ = Tag.objects.get_or_create(name="research")
            doc.tags.add(tag)
            logger.info("Stored research analysis as document %s", doc.id)

        return report
