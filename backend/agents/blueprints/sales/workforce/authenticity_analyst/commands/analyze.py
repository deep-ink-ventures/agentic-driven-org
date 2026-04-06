"""Authenticity Analyst command: analyze outreach pitches for AI-generated patterns."""

from agents.ai.archetypes.authenticity_analyst import COMMAND_DESCRIPTION
from agents.blueprints.base import command


@command(
    name="analyze",
    description=COMMAND_DESCRIPTION,
    model="claude-sonnet-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
