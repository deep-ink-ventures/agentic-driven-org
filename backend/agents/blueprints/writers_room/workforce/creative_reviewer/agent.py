"""Creative Reviewer — consolidates analyst feedback, scores quality, submits verdict.

Mirrors review_engineer in engineering: multiple specialist analysts feed into
one consolidator that produces a single structured verdict.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import EXCELLENCE_THRESHOLD
from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint
from agents.blueprints.writers_room.workforce.creative_reviewer.commands import review_creative

logger = logging.getLogger(__name__)


class CreativeReviewerBlueprint(WritersRoomFeedbackBlueprint):
    name = "Creative Reviewer"
    slug = "creative_reviewer"
    description = (
        "Consolidates analyst feedback and scores creative output quality — the quality gate for the writers room"
    )
    essential = True
    tags = ["review", "quality", "creative", "feedback"]
    review_dimensions = [
        "dramatic_action",
        "concept_fidelity",
        "originality",
        "market_fit",
        "structure",
        "character",
        "dialogue",
        "craft",
        "feasibility",
        "authenticity",
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

You receive reports from specialist analysts: market_analyst, structure_analyst, character_analyst, dialogue_analyst, format_analyst, production_analyst, authenticity_analyst. Each flags issues by severity (critical/major/minor/strength).

## DIMENSION 0 — DRAMATIC ACTION (THE GATE)

Before scoring any other dimension, answer:

Does this deliverable contain a story told through scenes where characters make decisions with visible consequences?

Test: Can you list at least 3 concrete scenes where a specific character does a specific thing that causes a specific result?

If NO: Overall score = 0. All other dimensions = 0. Verdict: CHANGES_REQUESTED. Write: "The deliverable does not contain dramatic action. It describes a concept but does not tell a story. No other dimension can be scored."

If YES: Proceed to dimensions 1-9. But Dramatic Action remains the floor — if it is the weakest dimension, it sets the overall score.

This check overrides all other scoring. A beautifully written, structurally sound, market-ready document that contains no dramatic action scores 0.

REVIEW DIMENSIONS (score each 1.0-10.0, use decimals):

1. **Concept Fidelity** — Does the output honor the creator's original pitch? Read the <project_goal> and check: are the creator's SPECIFIC characters, conflicts, arcs, and relationships preserved? If the creator said "three brothers" and the output has "a patriarch and his children," score 1-3. If characters, family structures, or conflicts were imported from reference shows instead of built from the pitch, score 1-3. Every major element in the output must trace back to something the creator specified.
2. **Originality** — Is this genuinely original? Apply the Setting Swap Test: if you change the setting back to a referenced show's setting, is the story the same? If yes, score 1-3. Apply the Character Swap Test: could you rename the characters to a referenced show's cast and the story still works? If yes, score 1-3.
3. **Market Fit** — Commercial viability, positioning, audience appeal
4. **Structure** — Story architecture, beats, pacing, act breaks
5. **Character** — Consistency, arcs, motivation, relationships, voice
6. **Dialogue** — Voice, subtext, scene construction, exposition balance
7. **Craft** — Format conventions, technical quality, polish
8. **Feasibility** — Budget, cast-ability, production practicality
9. **Authenticity** — Does the text read as genuinely human? AI linguistic tells, voice flattening, cliche density, coherence/hallucination.

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
- authenticity_analyst flags → lead_writer (voice/cliche issues) or story_architect (coherence/logic issues)

Include specific fix instructions in your report so the review loop knows what to route.

## CANON VERIFICATION (when Story Bible is present in context)

If a Story Bible is provided in the task context, perform canon verification:

For every character mentioned in the deliverable:
  - Does their behavior match established key decisions in the bible?
  - Do their relationships match the bible?
  - Does dialogue match voice directives?

For every scene:
  - Does it respect world rules?
  - Does it fit the established timeline?
  - Are there new facts that should be added to canon?

Any contradiction with [ESTABLISHED] items = critical failure (dimension score 0).
[TBD] items may be freely developed — but must be internally consistent.

## DRAMATIC WEAKNESS DETECTION

Beyond consistency, evaluate dramatic quality:

- **Logical threshold:** Does the cause-effect chain hold? Would a smart character make this decision given what they know? Plot-convenient stupidity = rejection.
- **Stakes calibration:** Proportional to the stage. Pitch needs existential stakes for the protagonist. Expose needs escalation. Treatment needs no scene without consequence. First draft needs every page to matter.
- **Dramatic economy:** If a subplot could be cut without the main arc collapsing, it's weak.

Scope scaling by stage:
- Pitch/expose: reject full storylines, character arcs, central conflicts that are weak
- Treatment/concept: reject scene sequences, subplot arcs, weak turning points
- First draft: reject individual scenes, dialogue decisions, weak beats

If the idea itself is wrong — not poorly executed but fundamentally weak — use verdict WEAK_IDEA instead of CHANGES_REQUESTED. WEAK_IDEA means: "this direction is wrong, try a different one." Your feedback says what is weak and why, but does NOT prescribe the replacement. The creative team must generate a fresh idea, not patch a bad one.

VERDICT OPTIONS:
- APPROVED: meets excellence threshold
- CHANGES_REQUESTED: execution needs improvement (revision loop)
- WEAK_IDEA: direction is fundamentally wrong (re-ideation loop)"""

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
