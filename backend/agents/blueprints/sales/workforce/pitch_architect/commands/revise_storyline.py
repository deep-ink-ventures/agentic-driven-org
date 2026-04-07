"""Pitch Architect command: revise storyline based on QA feedback."""

from agents.blueprints.base import command


@command(
    name="revise-storyline",
    description=(
        "Revise the outreach storyline based on QA feedback. Strengthen hooks, "
        "sharpen value proposition, improve anti-spam qualities."
    ),
    model="claude-opus-4-6",
)
def revise_storyline(self, agent) -> dict:
    return {
        "exec_summary": "Revise outreach storyline based on QA feedback",
        "step_plan": (
            "1. Review QA feedback on storyline effectiveness dimension\n"
            "2. Address each specific issue flagged\n"
            "3. Strengthen hooks and value proposition\n"
            "4. Improve anti-spam qualities\n"
            "5. Return revised storyline"
        ),
    }
