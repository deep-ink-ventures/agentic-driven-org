"""Story Researcher command: comprehensive market research and positioning."""

from agents.blueprints.base import command


@command(
    name="research",
    description=(
        "Full market research brief: comparable titles analysis (3-7 comps with what worked/failed), "
        "market positioning map, platform/publisher appetite, audience demographics and psychographics, "
        "cultural zeitgeist assessment, format requirements, and creative implications for the writing team"
    ),
    model="claude-sonnet-4-6",
)
def research(self, agent, **kwargs):
    pass  # Dispatched via execute_task
