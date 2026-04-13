"""Story Architect command: rewrite structure based on analyst feedback."""

from agents.blueprints.base import command


@command(
    name="fix_structure",
    description=(
        "Rewrite structural work based on severity-coded flags from the Structure Analyst "
        "and Format Analyst. Triages each flag by severity (critical rework, substantial "
        "revision, targeted fix), preserves elements marked as strengths, and produces a "
        "complete standalone structural document with a change manifest explaining what was "
        "revised and the structural reasoning behind each decision."
    ),
)
def fix_structure(self, agent, **kwargs):
    pass  # Dispatched via execute_task
