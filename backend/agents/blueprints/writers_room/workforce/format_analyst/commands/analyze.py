"""Format Analyst command: analyze formatting and craft standards."""

from agents.blueprints.base import command

DESCRIPTION = (
    "Assess industry format compliance (page count, margins, slug lines for screenplays; word count "
    "and chapter conventions for novels; stage direction standards for theatre). Evaluates craft quality "
    "including show-don't-tell ratio, prose density, white space balance, and readability pacing. "
    "Checks all format-specific conventions and flags deviations a professional reader would reject."
)


@command(
    name="analyze",
    description=DESCRIPTION,
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
