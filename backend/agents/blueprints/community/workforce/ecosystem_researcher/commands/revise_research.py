"""Ecosystem researcher command: revise research based on analyst feedback."""

from agents.blueprints.base import command


@command(
    name="revise-research",
    description=(
        "Refine ecosystem research based on analyst feedback. Fill gaps, re-assess flagged "
        "entries, explore missed categories or entities."
    ),
    model="claude-sonnet-4-6",
)
def revise_research(self, agent) -> dict:
    return {
        "exec_summary": "Revise ecosystem research based on analyst feedback",
        "step_plan": (
            "1. Review analyst feedback on gaps and issues\n"
            "2. Re-research flagged entities\n"
            "3. Explore missed categories\n"
            "4. Return revised ecosystem map"
        ),
    }
