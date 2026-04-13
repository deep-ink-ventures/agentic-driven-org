from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent


from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.marketing.leader.commands import (
    analyze_performance,
    create_campaign,
    create_content_calendar,
    create_priority_task,
)

logger = logging.getLogger(__name__)


class MarketingLeaderBlueprint(LeaderBlueprint):
    name = "Marketing Leader"
    slug = "leader"
    description = (
        "Marketing department leader — orchestrates campaigns, coordinates research and execution across all channels"
    )
    tags = ["leadership", "strategy", "campaigns", "coordination", "marketing"]
    skills = [
        {
            "name": "Prioritize Tasks",
            "description": "Analyze workforce activity and propose the highest-value initiative — coordinating one or multiple agents as needed",
        },
        {
            "name": "Design Campaigns",
            "description": "Create multi-channel campaigns with consistent branding, timing, and channel-appropriate messaging",
        },
        {
            "name": "Content Calendar",
            "description": "Plan coordinated content across all channels with day-by-day schedule and specific briefs",
        },
        {
            "name": "Analyze Performance",
            "description": "Compile reports from all agents, identify what's working, flag underperformers, suggest strategy adjustments",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are the marketing department leader. You orchestrate multi-channel marketing campaigns by coordinating your workforce agents: Web Researcher, Lu.ma Researcher, Reddit Specialist, Twitter Specialist, Email Marketing Specialist, and Content Reviewer.

Your core responsibilities:
1. Gather intelligence from research agents before making campaign decisions
2. Design campaigns with consistent branding, tone, and timing across all channels
3. Create tasks with clear instructions about messaging, angle, and what to link to
4. Schedule follow-up tasks to revisit campaigns and adjust strategy
5. Monitor performance and reallocate effort to what's working

You don't post directly — you create tasks for your workforce. Each task you create should include:
- Clear branding and tone guidance
- Channel-appropriate messaging
- Specific timing recommendations
- What angle to take and what to drive traffic toward

When creating campaigns, stagger content across channels for maximum impact. Research first, then execute."""

    # Register commands
    create_priority_task = create_priority_task
    create_campaign = create_campaign
    create_content_calendar = create_content_calendar
    analyze_performance = analyze_performance

    def generate_task_proposal(self, agent: Agent) -> dict:
        return self.create_priority_task(agent)
