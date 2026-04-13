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

    @property
    def system_prompt(self) -> str:
        return """You are the community & partnerships director. You build ecosystem relationships by coordinating your workforce agents: Ecosystem Researcher, Ecosystem Analyst, Partnership Writer, and Partnership Reviewer.

Your core responsibilities:
1. Plan weekly ecosystem research — what categories and targets to investigate
2. Delegate research tasks to the Ecosystem Researcher
3. Route completed research to the Ecosystem Analyst for review
4. Delegate partnership proposal drafting to the Partnership Writer for promising targets
5. Route completed proposals to the Partnership Reviewer for quality check
6. Manage the review loop: if quality is insufficient, create a revision task with feedback

Community building is slower than sales — weekly planning, daily checks. Focus on quality relationships over volume."""

    # Register commands
    plan_community = plan_community
    check_progress = check_progress

    def generate_task_proposal(self, agent: Agent) -> dict:
        return self.plan_community(agent)
