"""Dialog Writer command: draft dialogue for a specific scene."""

from agents.blueprints.base import command


@command(
    name="write_scene_dialogue",
    description=(
        "Construct a complete scene with fully realized dialogue, action lines, and "
        "stage direction. Establishes scene function (what changes by the end), maps "
        "power dynamics between characters, layers subtext beneath surface conversation, "
        "and differentiates each character's voice using the character bible."
    ),
    model="claude-opus-4-6",
)
def write_scene_dialogue(self, agent, **kwargs):
    pass  # Dispatched via execute_task
