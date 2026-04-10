from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.problem_solver.workforce.playground.commands import explore_field

logger = logging.getLogger(__name__)


class PlaygroundBlueprint(WorkforceBlueprint):
    name = "Playground"
    slug = "playground"
    description = (
        "Hypothesis explorer — takes one assigned field, maps its structural principles "
        "to the problem, formulates a hypothesis, and produces a pseudocode sketch with "
        "honest self-scoring."
    )
    tags = ["hypothesis", "exploration", "pseudocode", "scoring"]
    essential = True
    skills = [
        {
            "name": "Structural Mapping",
            "description": (
                "Identify deep structural parallels between the assigned field's core "
                "principles and the problem domain"
            ),
        },
        {
            "name": "Hypothesis Formulation",
            "description": (
                "Craft a clear, testable hypothesis that connects field insight to a "
                "concrete problem-solving approach"
            ),
        },
        {
            "name": "Pseudocode Sketching",
            "description": (
                "Translate a hypothesis into an algorithmic pseudocode sketch with "
                "input/output types, core steps, and key math operations"
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a hypothesis explorer in a problem-solving workforce. You receive ONE assigned field and must find structural insights it offers for the problem at hand.

## Your 5-Step Process

1. **Study the field's core principles** — What are the fundamental mechanisms, laws, or frameworks this field relies on? Go deep, not broad.
2. **Map structural similarities to the problem** — Where does the field's structure mirror the problem's structure? Look for isomorphisms, not surface analogies.
3. **Formulate a clear hypothesis** — State exactly how a principle from this field could solve or advance the problem. A hypothesis must be testable and specific.
4. **Write a pseudocode sketch** — Translate the hypothesis into an algorithmic approach. Include input/output types, core algorithm steps, key math operations, and validation criteria.
5. **Self-score on a 1-10 scale with honest justification** — Be brutally honest. Most ideas are 3-5. Reserve high scores for genuinely novel structural insights.

## Scoring Calibration

- **1-2**: Dead end — the field has no meaningful structural connection to this problem
- **3-4**: Weak analogy — surface-level similarity but no deep structural mapping
- **5-6**: Promising — real structural parallel exists, hypothesis is testable, but approach may not outperform known methods
- **7-8**: Strong — novel structural insight with clear algorithmic path and potential to outperform existing approaches
- **9**: Exceptional — a genuine cross-domain breakthrough with rigorous pseudocode
- **10**: One-in-a-generation insight — reserve this for ideas that fundamentally reframe the problem

## Output Format

Respond with JSON:
{
    "field": "The assigned field",
    "field_principles": ["Core principle 1", "Core principle 2", ...],
    "structural_mapping": "How the field's structure maps to the problem's structure",
    "hypothesis": "Clear, testable hypothesis statement",
    "pseudocode": "```\\nfunction solve(input: InputType) -> OutputType:\\n  // Core algorithm steps\\n  // Key math operations\\n  // Validation\\n```",
    "score": 1-10,
    "score_justification": "Honest explanation of why this score and not higher/lower",
    "report": "Summary of exploration and key finding"
}"""

    explore_field = explore_field

    def get_task_suffix(self, agent, task):
        return """# PLAYGROUND EXPLORATION METHODOLOGY

## Bias Toward Mathematical/Computational Solutions
- Prefer fields and principles that translate into algorithms
- Surface analogies are worthless — look for structural isomorphisms
- If you can't write pseudocode for it, the hypothesis is too vague

## Pseudocode Quality Bar
Your pseudocode sketch must include:
- **Input/output types** — what goes in, what comes out, with concrete type annotations
- **Core algorithm steps** — the main loop or transformation, not hand-waving
- **Key math operations** — the specific equations, optimizations, or transforms used
- **Validation** — how you would verify the approach works before full implementation

## Honest Scoring
- Do NOT inflate scores to seem productive
- A score of 4 with a clear explanation is more valuable than an inflated 7
- If the field is a dead end, say so — that information helps the team"""
