"""Leader command: plan a week of coordinated content."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(name="create-content-calendar", description="Plan a week of coordinated content across all channels")
def create_content_calendar(self, agent: Agent) -> dict:
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
Create a content calendar for the next 7 days. For each day, specify what each active agent should do.

Consider:
- Optimal posting times per channel
- Consistent messaging across channels
- Mix of content types (engagement, original content, research)
- Current campaign priorities

Respond with JSON:
{{
    "calendar_summary": "Overview of the week's strategy",
    "days": [
        {{
            "day": "Monday",
            "tasks": [
                {{
                    "target_agent_type": "twitter",
                    "exec_summary": "What to post",
                    "step_plan": "Detailed brief with tone/branding",
                    "proposed_exec_at": "ISO datetime"
                }}
            ]
        }}
    ]
}}"""

    response, _usage = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
        model=self.get_model(agent, command_name="create-content-calendar"),
    )

    try:
        data = json.loads(response)
        return {
            "calendar_summary": data.get("calendar_summary", response),
            "days": data.get("days", []),
        }
    except (json.JSONDecodeError, KeyError):
        return {"calendar_summary": response, "days": []}
