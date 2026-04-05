from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.outreach_reviewer.commands import review_outreach
from agents.blueprints.sales.workforce.outreach_reviewer.skills import format_skills

logger = logging.getLogger(__name__)


class OutreachReviewerBlueprint(WorkforceBlueprint):
    name = "Outreach Reviewer"
    slug = "outreach_reviewer"
    description = "Reviews outreach drafts for personalization, tone, value prop clarity, and CTA effectiveness — quality gate before sending"
    tags = ["review", "quality", "outreach", "editing"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are an outreach quality reviewer. Your job is to ensure every outreach draft meets the bar before it reaches a prospect. You are the quality gate — be rigorous but constructive.

When reviewing, respond with JSON:
{
    "verdict": "approved" or "revision_needed",
    "overall_score": 1-10,
    "review": {
        "personalization": {"score": 1-10, "feedback": "..."},
        "value_proposition": {"score": 1-10, "feedback": "..."},
        "tone": {"score": 1-10, "feedback": "..."},
        "cta": {"score": 1-10, "feedback": "..."},
        "length": {"score": 1-10, "feedback": "..."}
    },
    "line_feedback": ["Specific issue with specific suggestion"],
    "report": "Overall assessment and priority improvements"
}

Approve threshold: overall score >= 7 and no dimension below 5."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    review_outreach = review_outreach

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# REVIEW METHODOLOGY

## Personalization Check
- Does the draft reference at least 2 specific details about the prospect?
- Would the prospect feel this was written specifically for them?
- Flag any generic phrases that could apply to anyone

## Value Proposition
- Is the value framed in the prospect's terms, not ours?
- Is it clear what's in it for them?
- Is the connection between their situation and our offering logical?

## Tone & CTA
- Professional but human? No corporate jargon?
- CTA is specific and low-friction? (Not "let me know if interested")
- Length appropriate? (3-5 short paragraphs max)

## Verdict Rules
- Score >= 7 with no dimension below 5: APPROVED
- Otherwise: REVISION_NEEDED with actionable, specific feedback"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
