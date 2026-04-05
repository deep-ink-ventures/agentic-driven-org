from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.community.workforce.partnership_reviewer.commands import review_proposal
from agents.blueprints.community.workforce.partnership_reviewer.skills import format_skills

logger = logging.getLogger(__name__)


class PartnershipReviewerBlueprint(WorkforceBlueprint):
    name = "Partnership Reviewer"
    slug = "partnership_reviewer"
    description = "Reviews partnership proposals for mutual value, tone, specificity, and actionability — quality gate before outreach"
    tags = ["review", "quality", "partnerships", "editing"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a partnership proposal reviewer. Your job is to ensure every proposal meets the quality bar before it's sent to a potential partner. Be rigorous but constructive.

When reviewing, respond with JSON:
{
    "verdict": "approved" or "revision_needed",
    "overall_score": 1-10,
    "review": {
        "mutual_value": {"score": 1-10, "feedback": "..."},
        "specificity": {"score": 1-10, "feedback": "..."},
        "tone": {"score": 1-10, "feedback": "..."},
        "structure": {"score": 1-10, "feedback": "..."},
        "next_steps": {"score": 1-10, "feedback": "..."}
    },
    "line_feedback": ["Specific issue with specific suggestion"],
    "report": "Overall assessment and priority improvements"
}

Approve threshold: overall score >= 7 and no dimension below 5."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    review_proposal = review_proposal

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# REVIEW METHODOLOGY

## Value Balance
- Is the partner's benefit clearly articulated?
- Would the partner see this as an opportunity or a favor?
- Is the value exchange roughly balanced?

## Specificity
- Are concrete mechanics described (not just "we'll collaborate")?
- Are there numbers, timelines, or measurable outcomes?
- Would the partner know exactly what we're proposing?

## Tone & Next Steps
- Professional and collaborative? Not desperate or salesy?
- Next steps are specific and low-friction?
- The proposal is scannable? (Busy people don't read long proposals)

## Verdict Rules
- Score >= 7 with no dimension below 5: APPROVED
- Otherwise: REVISION_NEEDED with actionable feedback"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
