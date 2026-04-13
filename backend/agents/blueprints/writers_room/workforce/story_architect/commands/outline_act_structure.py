"""Story Architect command: break story into acts with turning points."""

from agents.blueprints.base import command


@command(
    name="outline_act_structure",
    description=(
        "Decompose the narrative into a precise act-by-act architecture with dramatic questions, "
        "turning points, midpoint reversal, and climax placement. Maps each act's emotional "
        "trajectory and pacing curve, identifies the gap between expectation and result at every "
        "act break (McKee), and validates that causality -- not coincidence -- drives each "
        "transition. Produces a visual tension map showing how energy escalates across the full arc."
    ),
)
def outline_act_structure(self, agent, **kwargs):
    pass  # Dispatched via execute_task
