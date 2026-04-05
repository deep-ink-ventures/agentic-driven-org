from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent


from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.sales.leader.commands import check_progress, plan_pipeline
from agents.blueprints.sales.leader.skills import format_skills

logger = logging.getLogger(__name__)


class SalesLeaderBlueprint(LeaderBlueprint):
    name = "Sales Director"
    slug = "leader"
    description = (
        "Sales department leader — orchestrates prospecting, outreach, and review cycles to build a qualified pipeline"
    )
    tags = ["leadership", "strategy", "sales", "pipeline", "prospecting"]
    config_schema = {}

    def get_review_pairs(self):
        return [
            {
                "creator": "outreach_writer",
                "creator_fix_command": "revise-outreach",
                "reviewer": "outreach_reviewer",
                "reviewer_command": "review-outreach",
                "dimensions": ["personalization", "value_proposition", "tone", "cta", "length"],
            },
        ]

    @property
    def system_prompt(self) -> str:
        return """You are the sales department director. You orchestrate outbound prospecting and outreach by coordinating your workforce agents: Prospector, Prospect Analyst, Outreach Writer, and Outreach Reviewer.

Your core responsibilities:
1. Plan daily pipeline activities — who to research, who to contact
2. Delegate research tasks to the Prospector for target qualification
3. Route completed prospect lists to the Prospect Analyst for review
4. Delegate outreach drafting to the Outreach Writer for qualified prospects
5. Route completed drafts to the Outreach Reviewer for quality check
6. Manage the review ping-pong loop: if a reviewer sends work back, create a revision task for the writer with the feedback

REVIEW CHAIN (AUTOMATIC — do not manually manage reviews):
When an outreach_writer task completes, the system automatically:
1. Routes the draft to the outreach_reviewer for quality check
2. If score < 9.5/10 → fix task auto-created for the writer with feedback
3. After fix → reviewer runs again (ping-pong until approved or max rounds)
4. After reaching 9.0, max 3 polish attempts to reach 9.5, then accept
Do NOT manually create review tasks — the system handles the loop.

You don't prospect or write outreach directly — you create tasks for your workforce."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    plan_pipeline = plan_pipeline
    check_progress = check_progress

    def generate_task_proposal(self, agent: Agent) -> dict:
        # Check for review cycle triggers first (universal from base class)
        review_result = self._check_review_trigger(agent)
        if review_result:
            return review_result
        return self.plan_pipeline(agent)
