"""Dialog Writer command: layer subtext into existing dialogue."""

from agents.blueprints.base import command


@command(
    name="rewrite_for_subtext",
    description=(
        "Take existing on-the-nose dialogue and rewrite it with layered subtext, "
        "power dynamics, and unspoken meaning. Identifies where characters say what they "
        "mean too directly, replaces with indirect expression through deflection, silence, "
        "subject changes, and loaded mundane conversation."
    ),
    model="claude-opus-4-6",
)
def rewrite_for_subtext(self, agent, **kwargs):
    pass  # Dispatched via execute_task
