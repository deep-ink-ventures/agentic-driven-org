"""Lead Writer command: write the expose document."""

from agents.blueprints.base import command


@command(
    name="write_expose",
    description=(
        "Synthesize creative agents' fragments into a 5-10 page expose. "
        "Three-movement architecture with marked turning points, character arcs "
        "showing transformation, sustained tonal throughline. Must reveal complete "
        "story including resolution."
    ),
    max_tokens=16384,
)
def write_expose(self, agent, **kwargs):
    pass  # Dispatched via execute_task
