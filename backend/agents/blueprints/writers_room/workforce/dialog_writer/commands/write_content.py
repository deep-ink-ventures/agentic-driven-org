"""Dialog Writer command: write content for current stage."""

from agents.blueprints.base import command


@command(
    name="write_content",
    description=(
        "Write the complete content -- dialogue, prose, scenes -- for the project at "
        "its current stage. Adapts output depth from a single logline sentence through "
        "full draft with complete scenes, dialogue blocks, and narrative prose. Builds "
        "on the Story Architect's structure and Character Designer's ensemble."
    ),
    model="claude-opus-4-6",
)
def write_content(self, agent, **kwargs):
    pass  # Dispatched via execute_task
