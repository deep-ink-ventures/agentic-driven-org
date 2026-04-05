"""Creative Reviewer — consolidates analyst feedback, scores quality, submits verdict.

Mirrors review_engineer in engineering: multiple specialist analysts feed into
one consolidator that produces a single structured verdict.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import EXCELLENCE_THRESHOLD, WorkforceBlueprint
from agents.blueprints.writers_room.workforce.creative_reviewer.commands import review_creative

logger = logging.getLogger(__name__)


class CreativeReviewerBlueprint(WorkforceBlueprint):
    name = "Creative Reviewer"
    slug = "creative_reviewer"
    description = (
        "Consolidates analyst feedback and scores creative output quality — the quality gate for the writers room"
    )
    tags = ["review", "quality", "creative", "feedback"]
    review_dimensions = [
        "concept_fidelity",
        "originality",
        "market_fit",
        "structure",
        "character",
        "dialogue",
        "craft",
        "feasibility",
    ]
    skills = [
        {
            "name": "Feedback Consolidation",
            "description": "Synthesize reports from multiple specialist analysts into a single quality assessment",
        },
        {
            "name": "Fix Routing",
            "description": "Map specific issues to the creative agent best equipped to fix them",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are the Creative Reviewer for the Writers Room. Your job is to consolidate feedback from all analyst agents and produce a single quality verdict.

You receive reports from specialist analysts: market_analyst, structure_analyst, character_analyst, dialogue_analyst, format_analyst, production_analyst. Each flags issues by severity (critical/major/minor/strength).

REVIEW DIMENSIONS (score each 1.0-10.0, use decimals):

1. **Concept Fidelity** — Does the output honor the creator's original pitch? Are specific characters, conflicts, arcs preserved and developed (not replaced with generic alternatives)?
2. **Originality** — Is this genuinely original? Apply the Setting Swap Test: if you change the setting back to a referenced show's setting, is the story the same? If yes, score 1-3.
3. **Market Fit** — Commercial viability, positioning, audience appeal
4. **Structure** — Story architecture, beats, pacing, act breaks
5. **Character** — Consistency, arcs, motivation, relationships, voice
6. **Dialogue** — Voice, subtext, scene construction, exposition balance
7. **Craft** — Format conventions, technical quality, polish
8. **Feasibility** — Budget, cast-ability, production practicality

Only score dimensions that were analyzed by feedback agents this round.
Always score concept_fidelity and originality — they apply at every stage.

SCORING:
- Overall score = MINIMUM of all dimension scores
- The bar is EXCELLENCE — {EXCELLENCE_THRESHOLD}/10 is the threshold

After your review, call the submit_verdict tool with your verdict and score.

FIX ROUTING (for CHANGES_REQUESTED):
Group issues by which creative agent should fix them:
- market_analyst flags → story_researcher
- structure_analyst flags → story_architect
- character_analyst flags → character_designer
- dialogue_analyst flags → dialog_writer
- format_analyst flags → story_architect (structural) or dialog_writer (craft)
- production_analyst flags → most relevant creative agent
- concept_fidelity / originality flags → story_architect AND character_designer

Include specific fix instructions in your report so the review loop knows what to route."""

    review_creative = review_creative

    def get_task_suffix(self, agent, task):
        return """# REVIEW METHODOLOGY

Read all analyst feedback reports from the department's recent completed tasks.
Consolidate findings, score each dimension, and submit your verdict.

## Verdict
The overall score is the MINIMUM of all dimension scores.
After your review, call the submit_verdict tool with your verdict and score.
For CHANGES_REQUESTED, include specific fix instructions grouped by creative agent."""

    def get_max_tokens(self, agent, task):
        return 12000
