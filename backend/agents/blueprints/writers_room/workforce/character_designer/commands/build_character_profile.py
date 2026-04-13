"""Character Designer command: generate deep character profile from concept."""

from agents.blueprints.base import command


@command(
    name="build_character_profile",
    description=(
        "Expand a character concept sketch into a full psychological profile. Delivers biography "
        "and formative backstory, the wound-want-need triangle, fatal flaw and blind spot, defining "
        "contradiction, behavioral patterns under pressure, and the complete arc trajectory with "
        "catalytic incident, point of no return, dark night, and transformation moment."
    ),
)
def build_character_profile(self, agent, **kwargs):
    pass  # Dispatched via execute_task
