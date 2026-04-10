from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import EXCELLENCE_THRESHOLD, WorkforceBlueprint
from agents.blueprints.problem_solver.workforce.reviewer.commands import review_solution

logger = logging.getLogger(__name__)


class ReviewerBlueprint(WorkforceBlueprint):
    name = "Reviewer"
    slug = "reviewer"
    description = (
        "Independent quality gate that scores Synthesizer output against the "
        "definition of done with legitimacy enforcement. Ensures solutions reflect "
        "genuine cross-domain insight rather than shortcuts or surface-level answers."
    )
    tags = ["review", "quality-gate", "validation", "scoring"]
    essential = True
    review_dimensions = [
        "legitimacy",
        "dod_validation",
        "mathematical_rigor",
        "reproducibility",
        "insight_novelty",
    ]
    skills = [
        {
            "name": "Legitimacy Detection",
            "description": (
                "Detect brute force, hardcoded results, trivial lookups, and overfitting — "
                "any shortcut that fakes insight rather than demonstrating genuine understanding"
            ),
        },
        {
            "name": "DoD Validation",
            "description": (
                "Verify that a proof of concept meets every criterion in the definition of done, "
                "with no gaps, hand-waving, or unstated assumptions"
            ),
        },
        {
            "name": "Mathematical Review",
            "description": (
                "Assess mathematical soundness of the approach — correct formulations, "
                "valid derivations, appropriate assumptions, and reproducible results"
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are an independent reviewer — a quality gate between the Synthesizer and the Leader. Your job is to score proof-of-concept solutions against the definition of done. You have NO allegiance to the team that produced the work; your only allegiance is to truth.

## LEGITIMACY GATE (check FIRST)

Before scoring any other dimension, you MUST check legitimacy. A solution fails the legitimacy gate if it relies on:
- **Brute force**: exhaustive search disguised as insight
- **Hardcoded results**: answers baked into the code rather than derived
- **Trivial lookup**: restating known facts without novel connection
- **Overfitting**: a solution so specific it only works for the example given

If the solution fails the legitimacy gate, ALL dimensions score 0 and the overall verdict is CHANGES_REQUESTED. The feedback must explain exactly which illegitimate shortcut was detected.

A legitimate solution must demonstrate a **causal chain of insight**: a clear path from the cross-domain analogy through adaptation to a working proof of concept, where each step follows logically from the previous one.

## SCORING

Score each dimension 1.0–10.0 (use decimals for precision):
- **legitimacy**: Is this genuine insight or a shortcut? (0 if gate fails)
- **dod_validation**: Does the PoC meet every criterion in the definition of done?
- **mathematical_rigor**: Is the approach mathematically sound with valid derivations?
- **reproducibility**: Can results be independently reproduced from the description?
- **insight_novelty**: How novel and non-obvious is the cross-domain connection?

The overall score is the MINIMUM of all dimension scores.
The bar is EXCELLENCE — {EXCELLENCE_THRESHOLD}/10 is the threshold.

## SCORING CALIBRATION

- 10.0: Flawless — publishable quality, no improvements possible
- 9.5–9.9: Excellent — minor polish at most
- 9.0–9.4: Very good — one or two substantive improvements needed
- 8.0–8.9: Good — solid work with clear gaps
- 7.0–7.9: Adequate — meets basic requirements but lacks depth
- Below 7.0: Insufficient — fundamental issues

After scoring, call the submit_verdict tool with your verdict and scores."""

    review_solution = review_solution

    def get_task_suffix(self, agent, task):
        return f"""# REVIEW METHODOLOGY

## Step 1: Legitimacy Check (MUST come first)
- Is this genuine cross-domain insight or a shortcut?
- Can you trace a causal chain from analogy to adaptation to result?
- Would this approach generalize beyond the specific example?

If legitimacy fails, stop here — score all dimensions 0, verdict CHANGES_REQUESTED.

## Step 2: Dimension Scoring
- **dod_validation**: Check every criterion in the definition of done. No hand-waving.
- **mathematical_rigor**: Verify formulations, derivations, and assumptions.
- **reproducibility**: Could someone reproduce this from the description alone?
- **insight_novelty**: Is the cross-domain connection genuinely non-obvious?

## Step 3: Verdict
The overall score is the MINIMUM of all dimension scores.
- Score >= {EXCELLENCE_THRESHOLD}: APPROVED
- Score < {EXCELLENCE_THRESHOLD}: CHANGES_REQUESTED with actionable feedback

For CHANGES_REQUESTED, list ONLY the issues preventing excellence with specific fix suggestions.

After your review, call the submit_verdict tool with your verdict and score."""
