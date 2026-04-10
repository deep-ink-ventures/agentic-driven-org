"""Reviewer command: independently score Synthesizer output against the DoD."""

from agents.blueprints.base import command


@command(
    name="review-solution",
    description=(
        "Score a Synthesizer's proof of concept against the definition of done. "
        "Check legitimacy first, then score all dimensions. Submit verdict via tool call."
    ),
    model="claude-opus-4-6",
)
def review_solution(self, agent) -> dict:
    return {
        "exec_summary": "Review proof of concept against definition of done",
        "step_plan": (
            "1. Check legitimacy — is this genuine insight or a shortcut?\n"
            "2. Score dod_validation — does the PoC meet the definition of done?\n"
            "3. Score mathematical_rigor — is the approach mathematically sound?\n"
            "4. Score reproducibility — can results be independently reproduced?\n"
            "5. Score insight_novelty — how novel is the cross-domain insight?\n"
            "6. Overall score = minimum of all dimensions\n"
            "7. Submit verdict via submit_verdict tool"
        ),
    }
