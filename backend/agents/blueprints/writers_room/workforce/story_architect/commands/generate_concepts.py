"""Story Architect command: generate competing concept pitches for ideation."""

from agents.blueprints.base import command


@command(
    name="generate_concepts",
    description=(
        "Generate 3-5 genuinely diverse concept pitches for the ideation stage, informed by "
        "market research and the project goal. Each pitch includes premise, format, genre, "
        "tone, target audience, zeitgeist hook, dramatic engine, and unique angle. Concepts "
        "deliberately vary across genre, format, tone, and audience to present real creative "
        "alternatives -- not five variations of the same idea."
    ),
)
def generate_concepts(self, agent, **kwargs):
    pass  # Dispatched via execute_task
