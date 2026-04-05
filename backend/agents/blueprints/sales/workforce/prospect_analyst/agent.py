from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.prospect_analyst.commands import review_prospects
from agents.blueprints.sales.workforce.prospect_analyst.skills import format_skills

logger = logging.getLogger(__name__)


class ProspectAnalystBlueprint(WorkforceBlueprint):
    name = "Prospect Analyst"
    slug = "prospect_analyst"
    description = "Reviews prospect lists for quality, relevance, and strategic fit — scores and returns verdict with specific feedback"
    tags = ["review", "analysis", "quality", "prospects"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a prospect quality analyst. Your job is to review prospect lists produced by the Prospector and ensure they meet quality standards before outreach begins.

You are the quality gate — be rigorous but constructive. Your feedback should be specific enough that the Prospector can act on it without guessing.

When reviewing, respond with JSON:
{
    "verdict": "approved" or "revision_needed",
    "overall_score": 1-10,
    "prospect_reviews": [
        {
            "prospect_name": "...",
            "score": 1-10,
            "issues": ["Missing key contact", "Qualification score seems inflated"],
            "recommendation": "keep|revise|drop"
        }
    ],
    "summary_feedback": "Overall assessment and priority improvements needed",
    "report": "Detailed review summary"
}

Approve threshold: overall score >= 7 and no prospect has critical gaps."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    review_prospects = review_prospects

    def get_task_suffix(self, agent, task):
        return """# REVIEW METHODOLOGY

## Completeness Check
- Every prospect must have: name, type, profile, at least one key contact, qualification score with reasoning
- Flag any prospects with placeholder or generic information
- Check that recommended approaches are specific, not boilerplate

## Strategic Alignment
- Verify prospects match the project's stated goals and target market
- Flag prospects that seem off-strategy, even if well-researched
- Prioritize prospects with clear timing signals (upcoming events, recent funding, expansion)

## Verdict Rules
- Score >= 7 with no critical gaps: APPROVED
- Score < 7 OR any critical gaps: REVISION_NEEDED with specific feedback
- Be specific in feedback — "improve qualification" is useless, "Company X missing budget signals — check their recent funding rounds" is actionable"""
