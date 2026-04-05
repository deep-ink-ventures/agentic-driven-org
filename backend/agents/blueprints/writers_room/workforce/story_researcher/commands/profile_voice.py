"""Story Researcher command: analyze source material for voice profile."""

from agents.blueprints.base import command


@command(
    name="profile_voice",
    description=(
        "Extract a Voice DNA profile from source material: sentence rhythm analysis with exact quotes, "
        "vocabulary fingerprint, tonal register, dialogue patterns, emotional temperature, distinctive tics, "
        "anti-patterns (what this voice is NOT), and concrete voice commandments for creative agents. "
        "Stored as an inviolable constraint for all subsequent writing."
    ),
    model="claude-sonnet-4-6",
)
def profile_voice(self, agent, **kwargs):
    pass  # Dispatched via execute_task
