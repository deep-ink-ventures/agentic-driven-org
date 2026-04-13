"""Lead Writer command: write the first draft (standalone only)."""

from agents.blueprints.base import command


@command(
    name="write_first_draft",
    description=(
        "Synthesize creative agents' fragments and the treatment into a full first draft. "
        "The actual screenplay, manuscript, or play script. Must be complete, not perfect. "
        "Medium-specific formatting. Standalone works only."
    ),
    max_tokens=65536,
)
def write_first_draft(self, agent, **kwargs):
    pass  # Dispatched via execute_task
