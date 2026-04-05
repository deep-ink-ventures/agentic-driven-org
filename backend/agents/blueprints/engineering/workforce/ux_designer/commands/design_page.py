"""UX Designer command: design a full page layout specification."""

from agents.blueprints.base import command


@command(
    name="design_page",
    description=(
        "Design a full page layout: information hierarchy, visual rhythm through varied spacing, "
        "grid structure with intentional asymmetry, component composition, responsive adaptation "
        "strategy (mobile-first with content-driven breakpoints), and the 'one memorable thing' "
        "that makes this page unforgettable. Includes wireframe-level specification with exact "
        "spacing values."
    ),
    model="claude-sonnet-4-6",
)
def design_page(self, agent, **kwargs):
    pass  # Dispatched via execute_task
