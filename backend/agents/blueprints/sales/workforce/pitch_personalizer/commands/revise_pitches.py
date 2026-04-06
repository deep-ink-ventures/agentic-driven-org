"""Pitch Personalizer command: revise pitches based on QA feedback."""

from agents.blueprints.base import command


@command(
    name="revise-pitches",
    description=(
        "Revise personalized pitches based on QA feedback. Deepen personalization, "
        "strengthen hooks, fix any generic or template-obvious elements."
    ),
    model="claude-sonnet-4-6",
)
def revise_pitches(self, agent) -> dict:
    return {
        "exec_summary": "Revise personalized pitches based on QA feedback",
        "step_plan": (
            "1. Review QA feedback on pitch personalization dimension\n"
            "2. Identify which pitches were flagged and why\n"
            "3. Deepen personalization with additional research\n"
            "4. Strengthen hooks and value propositions\n"
            "5. Return revised pitch payloads"
        ),
    }
