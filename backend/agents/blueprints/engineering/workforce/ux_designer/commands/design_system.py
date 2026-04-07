"""UX Designer command: define or extend a project's design system."""

from agents.blueprints.base import command


@command(
    name="design_system",
    description=(
        "Define or extend the project's design system: type scale (modular, fluid with clamp()), "
        "color system (OKLCH-based with tinted neutrals, 60-30-10 distribution), spacing scale "
        "(4pt base), elevation/depth system, component library inventory, motion principles, and "
        "dark mode strategy. Produces a .impeccable.md context file for the project."
    ),
    model="claude-opus-4-6",
)
def design_system(self, agent, **kwargs):
    pass  # Dispatched via execute_task
