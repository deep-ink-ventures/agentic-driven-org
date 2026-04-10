"""Pitch Personalizer command: find profiles and personalize pitches for one target area."""

from agents.blueprints.base import command


@command(
    name="personalize-pitches",
    description=(
        "For one target area: find real prospects via web search, research each person, "
        "adapt the storyline, and assign outreach channels."
    ),
    model="claude-haiku-4-5",
)
def personalize_pitches(self, agent) -> dict:
    return {
        "exec_summary": "Find profiles and personalize pitches for target area",
        "step_plan": (
            "1. Review the target area brief and narrative arc\n"
            "2. Search for real people matching this target area via web search\n"
            "3. For each person: verify identity, research recent activity\n"
            "4. Adapt the storyline hook, value prop, and CTA for each person\n"
            "5. Assign outreach channel from available agents\n"
            "6. Output structured pitch payloads"
        ),
    }
