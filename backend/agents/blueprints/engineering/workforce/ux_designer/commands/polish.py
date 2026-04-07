"""UX Designer command: refine a working but rough implementation."""

from agents.blueprints.base import command


@command(
    name="polish",
    description=(
        "Take a working but rough implementation and refine it: typography polish (vertical "
        "rhythm, proper font pairing, fluid sizing), color refinement (tinted neutrals, proper "
        "contrast), spacing rhythm (break monotony, group related, separate distinct), "
        "micro-interactions (state transitions, loading states), and visual details (shadows, "
        "borders, decorative elements that reinforce brand, NOT generic)."
    ),
    model="claude-opus-4-6",
)
def polish(self, agent, **kwargs):
    pass  # Dispatched via execute_task
