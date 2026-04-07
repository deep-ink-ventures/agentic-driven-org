"""Lead Writer command: write the treatment (standalone only)."""

from agents.blueprints.base import command


@command(
    name="write_treatment",
    description=(
        "Synthesize creative agents' fragments into a 20-40+ page treatment. "
        "Present tense, third person, scene by scene. Every scene turns a value. "
        "Subtext over dialogue. Progressive complications build relentlessly. "
        "Standalone works only (movie, play, book)."
    ),
    model="claude-opus-4-6",
    max_tokens=32768,
)
def write_treatment(self, agent, **kwargs):
    pass  # Dispatched via execute_task
