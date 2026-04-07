"""Pitch Architect command: design the outreach storyline."""

from agents.blueprints.base import command


@command(
    name="design-storyline",
    description=(
        "Craft the narrative arc for outreach — how we tell our story, why it matters, "
        "why someone would care, and how it avoids feeling like spam."
    ),
    model="claude-opus-4-6",
)
def design_storyline(self, agent) -> dict:
    return {
        "exec_summary": "Design the outreach storyline and narrative arc",
        "step_plan": (
            "1. Review research briefing and strategy for context\n"
            "2. Identify the core hook — what trigger event or pain point opens the door\n"
            "3. Design the narrative arc using AIDA structure\n"
            "4. Craft the value proposition framing in prospect terms\n"
            "5. Build objection preemption into the storyline\n"
            "6. Create variations for different target areas"
        ),
    }
