"""Story Architect command: write story structure for current project stage."""

from agents.blueprints.base import command


@command(
    name="write_structure",
    description=(
        "Build the complete structural framework for the current project stage -- from logline "
        "through revised draft. Selects the optimal narrative framework (three-act, five-act, "
        "Save the Cat, Story Circle, McKee, Truby, Vogler, Field) based on format and genre, "
        "then produces stage-appropriate deliverables: structural promise at logline, conflict "
        "architecture at expose, full beat-sheet roadmap at treatment, scene-by-scene causality "
        "chain at step outline, and beat-level backbone with pacing annotations at draft stages."
    ),
    model="claude-opus-4-6",
)
def write_structure(self, agent, **kwargs):
    pass  # Dispatched via execute_task
