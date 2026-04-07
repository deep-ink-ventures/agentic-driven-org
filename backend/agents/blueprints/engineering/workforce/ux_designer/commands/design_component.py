"""UX Designer command: create a detailed component design specification."""

from agents.blueprints.base import command


@command(
    name="design_component",
    description=(
        "Create a detailed component design spec: layout structure, typography choices "
        "(with specific font recommendations -- NO Inter/Roboto/Arial), color palette using OKLCH, "
        "spacing using 4pt grid system, all interactive states (hover, focus, active, disabled, "
        "loading, error, empty, populated), responsive behavior with container queries, motion "
        "design for state transitions (100/300/500ms timing), and accessibility requirements. "
        "Output is a complete spec document the frontend engineer can implement directly."
    ),
    model="claude-opus-4-6",
)
def design_component(self, agent, **kwargs):
    pass  # Dispatched via execute_task
