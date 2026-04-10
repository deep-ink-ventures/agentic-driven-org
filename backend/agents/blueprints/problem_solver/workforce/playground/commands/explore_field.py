"""Playground command: explore a single field for problem-solving insight."""

from agents.blueprints.base import command


@command(
    name="explore-field",
    description=(
        "Explore one assigned field — find applications that could generate insight "
        "for the problem. Produce a hypothesis + pseudocode sketch. Score 1-10."
    ),
    model="claude-opus-4-6",
)
def explore_field(self, agent) -> dict:
    return {
        "exec_summary": "Explore assigned field for problem-solving hypotheses",
        "step_plan": (
            "1. Study the assigned field's core principles\n"
            "2. Map structural similarities to the problem\n"
            "3. Formulate a clear hypothesis\n"
            "4. Write a pseudocode sketch of the algorithmic approach\n"
            "5. Self-score on 1-10 scale with honest justification"
        ),
    }
