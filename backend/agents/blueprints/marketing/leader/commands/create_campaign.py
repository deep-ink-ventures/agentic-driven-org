"""Leader command: design a multi-channel campaign."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(
    name="create-campaign", description="Design a multi-channel campaign with coordinated tasks for workforce agents"
)
def create_campaign(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude

    workforce = list(agent.department.agents.filter(status="active", is_leader=False).values_list("name", "agent_type"))
    workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

    context_msg = self.build_context_message(agent)
    msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Task
Design a multi-channel marketing campaign for this project. Create specific, coordinated tasks for the workforce agents.

For each task include:
- Clear branding and tone instructions
- Channel-appropriate messaging (professional for email, value-add for Reddit, engaging for Twitter)
- Specific timing (stagger across channels for maximum impact)
- What to link to and what angle to take

Also schedule a follow-up review task for yourself 30 days from now to assess campaign performance.

Respond with JSON:
{{
    "campaign_name": "Name of the campaign",
    "campaign_summary": "Brief strategy and rationale",
    "tasks": [
        {{
            "target_agent_type": "web_researcher",
            "exec_summary": "Research task for campaign preparation",
            "step_plan": "Detailed steps",
            "auto_execute": true
        }},
        {{
            "target_agent_type": "twitter",
            "exec_summary": "Twitter task with timing and messaging",
            "step_plan": "Detailed steps with branding guidance",
            "proposed_exec_at": "ISO datetime or null for immediate"
        }}
    ],
    "follow_up": {{
        "exec_summary": "Review campaign performance and adjust strategy",
        "days_from_now": 30
    }}
}}"""

    response, _usage = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
        model=self.get_model(agent, command_name="create-campaign"),
    )

    from agents.ai.claude_client import parse_json_response

    data = parse_json_response(response)
    if not data:
        logger.warning("Failed to parse create-campaign response: %s", response[:200])
        return None
    return {
        "campaign_name": data.get("campaign_name", "Campaign"),
        "campaign_summary": data.get("campaign_summary", ""),
        "tasks": data.get("tasks", []),
        "follow_up": data.get("follow_up"),
    }
