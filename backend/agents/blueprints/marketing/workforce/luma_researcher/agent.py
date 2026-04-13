from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.marketing.workforce.luma_researcher.commands import find_opportunities, scan_events

logger = logging.getLogger(__name__)


class LumaResearcherBlueprint(WorkforceBlueprint):
    name = "Lu.ma Researcher"
    slug = "luma_researcher"
    description = "Monitors Lu.ma event calendars for networking and speaking opportunities"
    tags = ["research", "events", "networking"]
    skills = [
        {"name": "Query Event Calendars", "description": "Check configured Lu.ma calendars for upcoming events"},
        {
            "name": "Extract Event Details",
            "description": "Get detailed information about specific events (speakers, topics, dates)",
        },
        {
            "name": "Identify Opportunities",
            "description": "Find events matching project goals for networking, speaking, or sponsorship",
        },
    ]
    config_schema = {
        "calendar_urls": {
            "type": "list",
            "required": True,
            "label": "Calendar URLs",
            "description": "Lu.ma calendar URLs to monitor for events",
        },
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

# EVENT ANALYSIS METHODOLOGY

## Relevance Scoring (three dimensions)
Score each event on:
- **Audience overlap**: how well does the event's expected attendance match the project's target audience?
- **Timing feasibility**: is there enough lead time to prepare and attend/participate?
- **Topic alignment**: how closely do the event's themes match current campaign goals?

Combine into an overall relevance rating: high (2+ dimensions strong), medium (1 strong), low (none strong).

## Opportunity Classification
For high-relevance events, classify the opportunity type:
- **Networking**: who specifically should be met and why (name roles, not just "industry leaders")
- **Speaking**: is there a CFP? What topic would position the project best?
- **Sponsorship**: what visibility tiers are available? Estimated cost vs reach?

## ROI Estimation
For each opportunity, estimate:
- Visibility reach (expected attendees, social amplification potential)
- Lead potential (how many target-audience contacts could this generate)
- Cost (time, money, materials needed)

## Follow-Up Action Plan
For each recommended event, specify:
- Preparation requirements (pitch deck, speaker bio, booth materials, RSVP deadline)
- Key contacts to connect with at the event
- Post-event follow-up actions and timeline

Respond with your events JSON and report."""

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
            model=self.get_model(agent),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        try:
            data = json.loads(response)
            return data.get("report", response)
        except (json.JSONDecodeError, KeyError):
            return response
