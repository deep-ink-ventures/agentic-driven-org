from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.community.workforce.ecosystem_analyst.commands import review_ecosystem

logger = logging.getLogger(__name__)


class EcosystemAnalystBlueprint(WorkforceBlueprint):
    name = "Ecosystem Analyst"
    slug = "ecosystem_analyst"
    description = "Reviews ecosystem research for completeness, strategic fit, and missed opportunities — quality gate before partnership outreach"
    tags = ["review", "analysis", "ecosystem", "strategy"]
    review_dimensions = ["coverage_completeness", "strategic_prioritization", "partnership_potential_accuracy"]
    skills = [
        {
            "name": "Strategic Prioritization",
            "description": "Rank ecosystem entities by reach, alignment, and effort-to-engage",
        },
        {
            "name": "Gap Analysis",
            "description": "Identify ecosystem categories or entities that should have been included but weren't",
        },
        {
            "name": "Competitive Landscape",
            "description": "Assess whether competitors already have relationships with identified entities",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are an ecosystem quality analyst. Your job is to review ecosystem research and ensure the map is comprehensive and strategically sound before partnership proposals begin.

When reviewing, respond with JSON:
{
    "entity_reviews": [
        {
            "entity_name": "...",
            "score": 1-10,
            "issues": ["Missing partnership angle", "Audience overlap unclear"],
            "recommendation": "keep|revise|drop"
        }
    ],
    "missing_categories": ["Categories or entities that should have been researched"],
    "summary_feedback": "Overall assessment and priority improvements",
    "report": "Detailed review summary"
}

Score each review dimension 1.0-10.0 (use decimals). The overall score is the MINIMUM of all dimension scores.
After your review, call the submit_verdict tool with your verdict and score."""

    review_ecosystem = review_ecosystem

    def get_task_suffix(self, agent, task):
        return """# REVIEW METHODOLOGY

## Coverage Check
- Are the obvious entities in this category represented?
- Are there adjacent categories that should have been explored?
- Is there geographic or demographic coverage that's missing?

## Strategic Assessment
- Do the partnership potential scores make sense given the project goals?
- Are there high-potential entities that were overlooked?
- Are any low-potential entities over-scored?

## Verdict Rules
The overall score is the MINIMUM of all dimension scores.
- Score >= 7 with no major coverage gaps: APPROVED
- Otherwise: CHANGES_REQUESTED with specific feedback on what to add or fix

After your review, call the submit_verdict tool with your verdict and score."""
