"""Character Designer command: create voice guide for a character."""

from agents.blueprints.base import command


@command(
    name="design_character_voice",
    description=(
        "Create a comprehensive voice guide for a single character. Covers vocabulary level and "
        "register, sentence rhythm and syntax preferences, verbal tics and pet phrases, rhetorical "
        "habits, what the character never says, and how their speech shifts under stress, intimacy, "
        "or authority. Includes sample dialogue lines demonstrating the voice in varied contexts."
    ),
    model="claude-opus-4-6",
)
def design_character_voice(self, agent, **kwargs):
    pass  # Dispatched via execute_task
