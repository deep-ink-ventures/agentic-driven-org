"""Lead Writer command: write the pitch document."""

from agents.blueprints.base import command


@command(
    name="write_pitch",
    description=(
        "Synthesize creative agents' fragments into a 2-3 page pitch document. "
        "Logline, world, characters, central conflict, tonality. Proves the story "
        "is worth telling. For series: conveys the story engine. For standalone: "
        "implies the complete arc."
    ),
    model="claude-sonnet-4-6",
    max_tokens=8192,
)
def write_pitch(self, agent, **kwargs):
    pass  # Dispatched via execute_task
