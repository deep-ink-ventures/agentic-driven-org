from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent


from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.community.leader.commands import check_progress, plan_community

logger = logging.getLogger(__name__)


class CommunityLeaderBlueprint(LeaderBlueprint):
    name = "Community Director"
    slug = "leader"
    description = "Community & partnerships leader — orchestrates ecosystem research, partnership proposals, and relationship building"
    tags = ["leadership", "strategy", "community", "partnerships", "ecosystem"]
    skills = [
        {
            "name": "Ecosystem Mapping",
            "description": "Categorize and track organizations, communities, events, and influencers by relevance and relationship stage",
        },
        {
            "name": "Partnership Strategy",
            "description": "Identify mutually beneficial partnership structures — referrals, co-marketing, cross-promotion, bundled offerings",
        },
        {
            "name": "Review Orchestration",
            "description": "Manage writer/reviewer ping-pong loops for partnership proposals — route drafts to reviewers, route feedback to writers",
        },
    ]
    config_schema = {}

    def get_review_pairs(self):
        return [
            {
                "creator": "partnership_writer",
                "creator_fix_command": "revise-proposal",
                "reviewer": "partnership_reviewer",
                "reviewer_command": "review-proposal",
                "dimensions": ["mutual_value", "specificity", "tone", "structure", "next_steps"],
            },
        ]

    @property
    def system_prompt(self) -> str:
        return """You are the community & partnerships director. You build ecosystem relationships by coordinating your workforce agents: Ecosystem Researcher, Ecosystem Analyst, Partnership Writer, and Partnership Reviewer.

Your core responsibilities:
1. Plan weekly ecosystem research — what categories and targets to investigate
2. Delegate research tasks to the Ecosystem Researcher
3. Route completed research to the Ecosystem Analyst for review
4. Delegate partnership proposal drafting to the Partnership Writer for promising targets
5. Route completed proposals to the Partnership Reviewer for quality check
6. Manage the review ping-pong loop: if a reviewer sends work back, create a revision task with feedback

REVIEW CHAIN (AUTOMATIC — do not manually manage reviews):
When a partnership_writer task completes, the system automatically:
1. Routes the proposal to the partnership_reviewer for quality check
2. If score < 9.5/10 → fix task auto-created for the writer with feedback
3. After fix → reviewer runs again (ping-pong until approved or max rounds)
4. After reaching 9.0, max 3 polish attempts to reach 9.5, then accept
Do NOT manually create review tasks — the system handles the loop.

Community building is slower than sales — weekly planning, daily checks. Focus on quality relationships over volume."""

    # Register commands
    plan_community = plan_community
    check_progress = check_progress

    def generate_task_proposal(self, agent: Agent) -> dict:
        # Check for review cycle triggers first (universal from base class)
        review_result = self._check_review_trigger(agent)
        if review_result:
            return review_result
        return self.plan_community(agent)
