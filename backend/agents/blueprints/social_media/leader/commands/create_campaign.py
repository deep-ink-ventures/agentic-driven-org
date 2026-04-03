"""Leader command: design a cross-platform campaign."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


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
