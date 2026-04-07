"""Pitch Personalizer command: personalize pitches for each prospect."""

from agents.blueprints.base import command


@command(
    name="personalize-pitches",
    description=(
        "For each prospect profile, research the person, adapt the storyline for them, "
        "and assign the best outreach channel from available agents."
    ),
    model="claude-opus-4-6",
)
def personalize_pitches(self, agent) -> dict:
    return {
        "exec_summary": "Personalize pitches for each prospect profile",
        "step_plan": (
            "1. Review the storyline from the pitch architect\n"
            "2. Review the profiles from the profile selector\n"
            "3. For each person: research their recent activity, interests, publications\n"
            "4. Adapt the storyline hook, value proposition, and CTA for this specific person\n"
            "5. Select the best outreach channel from available agents\n"
            "6. Output one structured pitch payload per person"
        ),
    }
