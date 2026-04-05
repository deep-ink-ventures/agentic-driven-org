"""Lead Writer command: write the series concept/bible."""

from agents.blueprints.base import command


@command(
    name="write_concept",
    description=(
        "Synthesize creative agents' fragments into a 15-25 page series concept/bible. "
        "Story engine, world rules, character ensemble as relationship web, saga arc, "
        "season one breakdown, episode overviews, future season sketches. "
        "Series works only (TV, film series, audio drama series)."
    ),
    model="claude-sonnet-4-6",
    max_tokens=32768,
)
def write_concept(self, agent, **kwargs):
    pass  # Dispatched via execute_task
