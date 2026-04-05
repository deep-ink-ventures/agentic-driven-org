from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import EXCELLENCE_THRESHOLD, WorkforceBlueprint
from agents.blueprints.sales.workforce.outreach_reviewer.commands import review_outreach

logger = logging.getLogger(__name__)


class OutreachReviewerBlueprint(WorkforceBlueprint):
    name = "Outreach Reviewer"
    slug = "outreach_reviewer"
    description = "Reviews outreach drafts for personalization, tone, value prop clarity, and CTA effectiveness — quality gate before sending"
    tags = ["review", "quality", "outreach", "editing"]
    review_dimensions = ["personalization", "value_proposition", "tone", "cta", "length"]
    skills = [
        {
            "name": "Tone Analysis",
            "description": "Assess professional tone — confidence without pushiness, authenticity without informality",
        },
        {
            "name": "Personalization Depth",
            "description": "Check that messaging references specific prospect details, not generic templates",
        },
        {
            "name": "Effectiveness Scoring",
            "description": "Score likelihood of response based on outreach best practices — subject line, opening, CTA strength",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are an outreach quality reviewer. Your job is to ensure every outreach draft meets the bar before it reaches a prospect. You are the quality gate — be rigorous but constructive.

When reviewing, score each dimension 1.0-10.0 (use decimals).
The overall score is the MINIMUM of all dimension scores.
The bar is EXCELLENCE — {EXCELLENCE_THRESHOLD}/10 is the threshold.

After your review, call the submit_verdict tool with your verdict and score.

Score dimensions: personalization, value_proposition, tone, cta, length.
For CHANGES_REQUESTED, list ONLY the issues preventing excellence with specific fix suggestions."""

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
- Score >= {EXCELLENCE_THRESHOLD}: APPROVED
- Score < {EXCELLENCE_THRESHOLD}: CHANGES_REQUESTED with actionable, specific feedback

After your review, call the submit_verdict tool with your verdict and score."""
