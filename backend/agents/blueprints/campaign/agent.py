from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import BaseBlueprint
from agents.blueprints.campaign.skills import format_skills

logger = logging.getLogger(__name__)


class CampaignBlueprint(BaseBlueprint):
    name = "Campaign Agent"
    slug = "campaign"
    description = "Orchestrates cross-platform campaigns and delegates to subordinate agents"

    @property
    def system_prompt(self) -> str:
        return """You are a campaign orchestration agent. Your role is to design and coordinate cross-platform social media campaigns, delegating execution to your subordinate agents (Twitter, Reddit, etc.).

You operate within a department and have a high-level view of the project's goals, branding, and all agent activity. You are the superior agent — you create and delegate tasks to subordinate agents.

When executing tasks, respond with a JSON object:
{
    "delegated_tasks": [
        {
            "target_agent_type": "twitter",
            "exec_summary": "What the Twitter agent should do",
            "step_plan": "Detailed steps for the Twitter agent"
        },
        {
            "target_agent_type": "reddit",
            "exec_summary": "What the Reddit agent should do",
            "step_plan": "Detailed steps for the Reddit agent"
        }
    ],
    "report": "Campaign strategy summary and delegation rationale"
}

Focus on strategic coordination. You don't post directly — you orchestrate."""

    @property
    def hourly_prompt(self) -> str:
        return """Review the current state of all active campaigns and subordinate agent activity:
1. Check recent task reports from subordinate agents
2. Identify any gaps in campaign execution
3. Delegate any needed follow-up tasks to subordinates
4. Assess if campaign strategy needs adjustment"""

    @property
    def task_generation_prompt(self) -> str:
        return """Based on the current project context, department activity, and campaign status, propose the single highest-value campaign action you could take.

Consider:
- Is there an opportunity for a new campaign?
- Do existing campaigns need adjustment?
- Are subordinate agents aligned and productive?
- Is there a time-sensitive opportunity to capitalize on?

Respond with JSON:
{
    "exec_summary": "One-line description of the campaign action",
    "step_plan": "Detailed step-by-step plan"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        task_msg = f"""{context_msg}

# Task to Execute
**Summary:** {task.exec_summary}
**Plan:** {task.step_plan}

Execute this task now. If you need to delegate to subordinate agents, include delegated_tasks in your response."""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
        )

        try:
            data = json.loads(response)
            delegated = data.get("delegated_tasks", [])
            report = data.get("report", response)

            if delegated:
                from agents.models import Agent as AgentModel, AgentTask as TaskModel
                subordinates = AgentModel.objects.filter(superior=agent, is_active=True)
                sub_by_type = {s.agent_type: s for s in subordinates}

                for dt in delegated:
                    target_type = dt.get("target_agent_type")
                    target_agent = sub_by_type.get(target_type)
                    if not target_agent:
                        logger.warning("No active subordinate of type %s for agent %s", target_type, agent.name)
                        continue

                    sub_task = TaskModel.objects.create(
                        agent=target_agent,
                        created_by_agent=agent,
                        status=TaskModel.Status.QUEUED,
                        auto_execute=True,
                        exec_summary=dt.get("exec_summary", "Delegated task"),
                        step_plan=dt.get("step_plan", ""),
                    )
                    from agents.tasks import execute_agent_task
                    execute_agent_task.delay(str(sub_task.id))
                    logger.info("Delegated task %s to %s", sub_task.id, target_agent.name)

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        msg = f"""{context_msg}

# Task Proposal Request
{self.task_generation_prompt}"""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=msg,
        )

        try:
            data = json.loads(response)
            return {
                "exec_summary": data.get("exec_summary", "Campaign coordination task"),
                "step_plan": data.get("step_plan", response),
            }
        except (json.JSONDecodeError, KeyError):
            return {"exec_summary": "Campaign coordination task", "step_plan": response}
