"""Prospector command: revise prospect list based on analyst feedback."""

from agents.blueprints.base import command


@command(
    name="revise-prospects",
    description=(
        "Refine a prospect list based on analyst feedback. Address specific gaps flagged in the review, "
        "re-research weak entries, add missing context, and improve qualification scoring."
    ),
    model="claude-sonnet-4-6",
)
def revise_prospects(self, agent) -> dict:
    return {
        "exec_summary": "Revise prospect list based on analyst feedback",
        "step_plan": (
            "1. Review analyst feedback on each flagged prospect\n"
            "2. Re-research entries with gaps\n"
            "3. Add missing context and contacts\n"
            "4. Update qualification scores\n"
            "5. Return revised list"
        ),
    }
