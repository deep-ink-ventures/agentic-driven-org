"""Creative reviewer command: consolidate feedback and score creative output."""

from agents.blueprints.base import command


@command(
    name="review-creative",
    description=(
        "Consolidate feedback from all analysts for a creative stage. "
        "Score each dimension 1-10, overall = minimum. "
        "Submit verdict via tool call."
    ),
    model="claude-sonnet-4-6",
)
def review_creative(self, agent) -> dict:
    return {
        "exec_summary": "Consolidate analyst feedback and score creative output",
        "step_plan": (
            "1. Read all analyst feedback reports for the current stage\n"
            "2. Score each dimension (concept fidelity, originality, market fit, structure, character, dialogue, craft, feasibility)\n"
            "3. Overall score = minimum of all scored dimensions\n"
            "4. Call submit_verdict tool with verdict and score\n"
            "5. For CHANGES_REQUESTED: include specific fix instructions grouped by which creative agent should address them"
        ),
    }
