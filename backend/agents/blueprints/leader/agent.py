from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.leader.skills import format_skills
from agents.blueprints.leader import commands

logger = logging.getLogger(__name__)


class DepartmentLeaderBlueprint(LeaderBlueprint):
    name = "Department Leader"
    slug = "leader"
    description = "Department leader — proposes priority tasks and campaigns, delegates to workforce agents"

    @property
    def system_prompt(self) -> str:
        return """You are the department leader agent. Your role is to analyze the project's goals, department context, and workforce agent capabilities to determine the highest-value actions.

You don't execute tasks directly on platforms — you create and delegate tasks to your workforce agents (Twitter, Reddit, etc.).

Your core responsibilities:
1. Propose the single most impactful next task for the department
2. Design cross-platform campaigns when opportunities arise
3. Ensure workforce agents are aligned with the project goal
4. Monitor department activity and adjust strategy

Always consider the project goal, department documents (branding guidelines, etc.), and what the workforce has been doing recently."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands from commands.py
    create_priority_task = commands.create_priority_task
    create_campaign = commands.create_campaign

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude
        from agents.models import Agent as AgentModel, AgentTask as TaskModel

        context_msg = self.build_context_message(agent)
        workforce = list(
            agent.department.agents.filter(is_active=True, is_leader=False)
            .values_list("name", "agent_type")
        )
        workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

        task_msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Task to Execute
**Summary:** {task.exec_summary}
**Plan:** {task.step_plan}

Execute this task. If it involves delegating work to workforce agents, include delegated_tasks in your response.

Respond with JSON:
{{
    "delegated_tasks": [
        {{
            "target_agent_type": "twitter or reddit",
            "exec_summary": "What the agent should do",
            "step_plan": "Detailed steps"
        }}
    ],
    "report": "Summary of what was decided and why"
}}"""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
        )

        try:
            data = json.loads(response)
            delegated = data.get("delegated_tasks", [])
            report = data.get("report", response)

            if delegated:
                workforce_agents = AgentModel.objects.filter(
                    department=agent.department,
                    is_active=True,
                    is_leader=False,
                )
                agents_by_type = {a.agent_type: a for a in workforce_agents}

                for dt in delegated:
                    target_type = dt.get("target_agent_type")
                    target_agent = agents_by_type.get(target_type)
                    if not target_agent:
                        logger.warning("No active workforce agent of type %s in department %s", target_type, agent.department.name)
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
                    logger.info("Leader delegated task %s to %s", sub_task.id, target_agent.name)

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        return self.create_priority_task(agent)
