"""Structure Analyst command: analyze narrative structure."""

from agents.blueprints.base import command

DESCRIPTION = (
    "Perform act structure compliance testing and beat sheet analysis against 2-3 best-fit "
    "frameworks (Save the Cat, McKee, Truby, Field, Vogler, Harmon, etc.). Includes pacing rhythm "
    "mapping with scene-by-scene energy curves, causality chain verification across plot threads, "
    "subplot integration assessment, and midpoint/climax evaluation with specific page or chapter references."
)


@command(
    name="analyze",
    description=DESCRIPTION,
    model="claude-opus-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
