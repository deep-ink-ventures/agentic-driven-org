"""Dialog Writer command: rewrite content based on analyst feedback."""

from agents.blueprints.base import command


@command(
    name="fix_content",
    description=(
        "Rewrite content based on Dialogue Analyst and Format Analyst feedback flags. "
        "Addresses voice differentiation failures, on-the-nose dialogue, exposition dumps, "
        "rhythm monotony, weak scene buttons, unfilmables, and format violations. Produces "
        "a complete revised document with a change log, not a diff."
    ),
    model="claude-opus-4-6",
)
def fix_content(self, agent, **kwargs):
    pass  # Dispatched via execute_task
