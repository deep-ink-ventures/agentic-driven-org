"""
Leader commands — Python methods registered as commands via the @command decorator.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(name="create-priority-task", description="Propose the highest-value next task for a workforce agent")
def create_priority_task(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude
    from agents.models import AgentTask

    workforce = list(
        agent.department.agents.filter(is_active=True, is_leader=False)
        .values_list("id", "name", "agent_type")
    )
    if not workforce:
        return {"exec_summary": "No workforce agents in department", "step_plan": ""}

    workforce_desc = "\n".join(f"- {name} ({atype})" for _, name, atype in workforce)

    awaiting_by_agent = {}
    for wid, wname, wtype in workforce:
        count = AgentTask.objects.filter(agent_id=wid, status=AgentTask.Status.AWAITING_APPROVAL).count()
        awaiting_by_agent[wname] = count

    awaiting_text = "\n".join(f"- {name}: {count} tasks awaiting approval" for name, count in awaiting_by_agent.items())

    context_msg = self.build_context_message(agent)
    msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Current Approval Queue
{awaiting_text}

# Task
Propose the single highest-value task for one of the workforce agents above. Consider the project goal, department documents, recent activity, and what each agent is already working on.

Respond with JSON:
{{
    "target_agent_type": "twitter or reddit (which workforce agent should do this)",
    "exec_summary": "One-line description of the task",
    "step_plan": "Detailed step-by-step plan"
}}"""

    response = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
    )

    try:
        data = json.loads(response)
        return {
            "target_agent_type": data.get("target_agent_type"),
            "exec_summary": data.get("exec_summary", "Priority task"),
            "step_plan": data.get("step_plan", response),
        }
    except (json.JSONDecodeError, KeyError):
        return {"exec_summary": "Priority task", "step_plan": response}


@command(name="create-campaign", description="Design a cross-platform campaign with coordinated tasks for workforce agents")
def create_campaign(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude

    workforce = list(
        agent.department.agents.filter(is_active=True, is_leader=False)
        .values_list("name", "agent_type")
    )
    workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

    context_msg = self.build_context_message(agent)
    msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Task
Design a cross-platform campaign for this project. Create specific, coordinated tasks for the workforce agents listed above.

Respond with JSON:
{{
    "campaign_name": "Name of the campaign",
    "campaign_summary": "Brief campaign description and rationale",
    "tasks": [
        {{
            "target_agent_type": "twitter",
            "exec_summary": "What this agent should do for the campaign",
            "step_plan": "Detailed steps"
        }},
        {{
            "target_agent_type": "reddit",
            "exec_summary": "What this agent should do for the campaign",
            "step_plan": "Detailed steps"
        }}
    ]
}}"""

    response = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
    )

    try:
        data = json.loads(response)
        return {
            "campaign_name": data.get("campaign_name", "Campaign"),
            "campaign_summary": data.get("campaign_summary", response),
            "tasks": data.get("tasks", []),
        }
    except (json.JSONDecodeError, KeyError):
        return {"campaign_name": "Campaign", "campaign_summary": response, "tasks": []}
