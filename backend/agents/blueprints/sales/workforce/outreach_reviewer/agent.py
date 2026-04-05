from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import EXCELLENCE_THRESHOLD, WorkforceBlueprint
from agents.blueprints.sales.workforce.outreach_reviewer.commands import review_outreach
from agents.blueprints.sales.workforce.outreach_reviewer.skills import format_skills

logger = logging.getLogger(__name__)


class OutreachReviewerBlueprint(WorkforceBlueprint):
    name = "Outreach Reviewer"
    slug = "outreach_reviewer"
    description = "Reviews outreach drafts for personalization, tone, value prop clarity, and CTA effectiveness — quality gate before sending"
    tags = ["review", "quality", "outreach", "editing"]
    review_dimensions = ["personalization", "value_proposition", "tone", "cta", "length"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are an outreach quality reviewer. Your job is to ensure every outreach draft meets the bar before it reaches a prospect. You are the quality gate — be rigorous but constructive.

When reviewing, score each dimension 1.0-10.0 (use decimals).
The overall score is the MINIMUM of all dimension scores.
The bar is EXCELLENCE — {EXCELLENCE_THRESHOLD}/10 is the threshold.

End your report with exactly one of these lines:
VERDICT: APPROVED (score: N.N/10)
VERDICT: CHANGES_REQUESTED (score: N.N/10)

Score dimensions: personalization, value_proposition, tone, cta, length.
For CHANGES_REQUESTED, list ONLY the issues preventing excellence with specific fix suggestions."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    review_outreach = review_outreach

    def get_task_suffix(self, agent, task):
        return f"""# REVIEW METHODOLOGY

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
The overall score is the MINIMUM of all dimension scores.
- Score >= {EXCELLENCE_THRESHOLD}: VERDICT: APPROVED (score: N.N/10)
- Score < {EXCELLENCE_THRESHOLD}: VERDICT: CHANGES_REQUESTED (score: N.N/10) with actionable, specific feedback

End your report with exactly one VERDICT line."""
