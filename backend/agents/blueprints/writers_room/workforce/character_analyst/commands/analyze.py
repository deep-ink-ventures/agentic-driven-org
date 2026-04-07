"""Character Analyst command: analyze character consistency and logic."""

from agents.blueprints.base import command

DESCRIPTION = (
    "Run a character consistency audit against established traits, arc progression tracking, and "
    "ensemble balance analysis (screen time equity across the cast). Evaluates motivation clarity, "
    "relationship dynamic shifts, the 'could you tell who is speaking' voice distinction test, and "
    "want-vs-need tension for all principal characters. Each flag cites the specific scene or chapter."
)


@command(
    name="analyze",
    description=DESCRIPTION,
    model="claude-opus-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
