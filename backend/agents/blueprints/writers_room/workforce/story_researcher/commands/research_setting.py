"""Story Researcher command: deep-dive world and setting research."""

from agents.blueprints.base import command


@command(
    name="research_setting",
    description=(
        "Deep authenticity research into the project's world: specific locations and geography, "
        "power structures and institutions, social hierarchies and insider language, historical events "
        "and real figures for fictionalization, cultural texture and generational dynamics, "
        "and scene-ready details for the writing team"
    ),
)
def research_setting(self, agent, **kwargs):
    pass  # Dispatched via execute_task
