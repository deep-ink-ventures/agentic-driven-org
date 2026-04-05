from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.community.workforce.ecosystem_analyst.commands import review_ecosystem
from agents.blueprints.community.workforce.ecosystem_analyst.skills import format_skills

logger = logging.getLogger(__name__)


class EcosystemAnalystBlueprint(WorkforceBlueprint):
    name = "Ecosystem Analyst"
    slug = "ecosystem_analyst"
    description = "Reviews ecosystem research for completeness, strategic fit, and missed opportunities — quality gate before partnership outreach"
    tags = ["review", "analysis", "ecosystem", "strategy"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are an ecosystem quality analyst. Your job is to review ecosystem research and ensure the map is comprehensive and strategically sound before partnership proposals begin.

When reviewing, respond with JSON:
{
    "verdict": "approved" or "revision_needed",
    "overall_score": 1-10,
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

Approve threshold: overall score >= 7 and no critical gaps in coverage."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    review_ecosystem = review_ecosystem

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# REVIEW METHODOLOGY

## Coverage Check
- Are the obvious entities in this category represented?
- Are there adjacent categories that should have been explored?
- Is there geographic or demographic coverage that's missing?

## Strategic Assessment
- Do the partnership potential scores make sense given the project goals?
- Are there high-potential entities that were overlooked?
- Are any low-potential entities over-scored?

## Verdict Rules
- Score >= 7 with no major coverage gaps: APPROVED
- Otherwise: REVISION_NEEDED with specific feedback on what to add or fix"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
