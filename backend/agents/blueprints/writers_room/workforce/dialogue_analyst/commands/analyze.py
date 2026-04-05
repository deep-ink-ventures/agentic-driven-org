"""Dialogue Analyst command: analyze dialogue quality and scene construction."""

from agents.blueprints.base import command

DESCRIPTION = (
    "Perform voice distinction analysis (can you identify speakers without attribution tags), "
    "subtext quality assessment (what is said vs what is meant), and power dynamic shift tracking "
    "within scenes. Evaluates exposition management for natural information delivery, scene rhythm "
    "and pacing, AI-voice detection, and voice fidelity against the author's DNA profile when available."
)


@command(
    name="analyze",
    description=DESCRIPTION,
    model="claude-sonnet-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
