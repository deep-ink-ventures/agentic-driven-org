from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.marketing.workforce.web_researcher.skills import format_skills
from agents.blueprints.marketing.workforce.web_researcher.commands import research_trends, research_competitors, find_content_opportunities

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
    research_trends = research_trends
    research_competitors = research_competitors
    find_content_opportunities = find_content_opportunities

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude
        from integrations.websearch.service import search

        # Extract search query from task
        query = task.exec_summary or ""
        search_results = search(query)

        suffix = f"""Here are the web search results to analyze:

<search_results>
{json.dumps(search_results, default=str, indent=2) if search_results else 'No results found.'}
</search_results>

Respond with your findings JSON and report."""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        from agents.ai.claude_client import parse_json_response
        from projects.models import Document, Tag

        data = parse_json_response(response)
        report = data.get("report", response) if data else response

        # Store research findings as a department document
        department = agent.department
        findings = data.get("findings", []) if data else []
        if findings:
            doc_content = f"# Research: {task.exec_summary}\n\n"
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
            )
            tag, _ = Tag.objects.get_or_create(name="research")
            doc.tags.add(tag)
            logger.info("Stored research findings as document %s", doc.id)

        return report
