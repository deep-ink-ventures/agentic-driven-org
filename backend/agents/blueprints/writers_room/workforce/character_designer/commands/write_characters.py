"""Character Designer command: design character ensemble for current stage."""

from agents.blueprints.base import command


@command(
    name="write_characters",
    description=(
        "Design the full character ensemble as a character bible: background and biography, "
        "psychological profile (want vs. need, fatal flaw, wound), speech patterns and verbal tics, "
        "relationship dynamics with every other main character, arc trajectory with turning points, "
        "and specific scene suggestions that establish each character. Depth scales with project stage."
    ),
)
def write_characters(self, agent, **kwargs):
    pass  # Dispatched via execute_task
