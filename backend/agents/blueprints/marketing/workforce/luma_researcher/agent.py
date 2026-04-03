from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.marketing.workforce.luma_researcher.skills import format_skills
from agents.blueprints.marketing.workforce.luma_researcher.commands import scan_events, find_opportunities

logger = logging.getLogger(__name__)


class LumaResearcherBlueprint(WorkforceBlueprint):
    name = "Lu.ma Researcher"
    slug = "luma_researcher"
    description = "Monitors Lu.ma event calendars for networking and speaking opportunities"
    tags = ["research", "events", "networking"]
    config_schema = {
        "calendar_urls": {"type": "list", "required": True, "description": "Lu.ma calendar URLs to monitor"},
    }

    @property
    def system_prompt(self) -> str:
        return """You are an event research agent. Monitor Lu.ma calendars for upcoming events relevant to the project. Identify networking, speaking, and sponsorship opportunities. Report event timing, audience, and relevance to project goals.

When executing tasks, respond with a JSON object:
{
    "events": [
        {"name": "...", "date": "...", "url": "...", "type": "networking|speaking|sponsorship", "relevance": "high|medium|low", "summary": "..."}
    ],
    "report": "Summary of events found and recommended actions"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    scan_events = scan_events
    find_opportunities = find_opportunities

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude
        from integrations.luma.service import query_events

        calendar_urls = agent.config.get("calendar_urls", [])
        events = query_events(calendar_urls)

        suffix = f"""Here are the Lu.ma events to analyze:

<luma_events>
{json.dumps(events, default=str, indent=2) if events else 'No events found.'}
</luma_events>

Respond with your events JSON and report."""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        try:
            data = json.loads(response)
            return data.get("report", response)
        except (json.JSONDecodeError, KeyError):
            return response
