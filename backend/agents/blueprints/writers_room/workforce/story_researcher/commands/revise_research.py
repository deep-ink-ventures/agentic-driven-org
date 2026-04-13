"""Story Researcher command: revise research based on analyst feedback."""

from agents.blueprints.base import command


@command(
    name="revise_research",
    description=(
        "Revise and update the research brief based on Market Analyst feedback flags. "
        "Addresses each flagged issue with updated analysis, corrected data, or additional research. "
        "Produces a complete, standalone updated brief — not a diff."
    ),
)
def revise_research(self, agent, **kwargs):
    pass  # Dispatched via execute_task
