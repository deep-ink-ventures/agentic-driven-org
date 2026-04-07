"""Character Designer command: revise characters based on analyst feedback."""

from agents.blueprints.base import command


@command(
    name="fix_characters",
    description=(
        "Revise the character ensemble based on Character Analyst feedback flags. "
        "Addresses want-vs-need clarity, action plausibility, consistency drift, "
        "relationship arc progression, secondary character distinctiveness, and knowledge-tracking "
        "errors. Produces a complete standalone character document with a change log."
    ),
    model="claude-opus-4-6",
)
def fix_characters(self, agent, **kwargs):
    pass  # Dispatched via execute_task
