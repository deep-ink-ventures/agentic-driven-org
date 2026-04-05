"""Outreach writer command: revise outreach based on reviewer feedback."""

from agents.blueprints.base import command


@command(
    name="revise-outreach",
    description=(
        "Revise an outreach draft based on reviewer feedback. Address specific issues: "
        "tone, personalization depth, value prop clarity, CTA strength."
    ),
    model="claude-sonnet-4-6",
)
def revise_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Revise outreach draft based on reviewer feedback",
        "step_plan": (
            "1. Review reviewer's specific feedback points\n"
            "2. Address each issue in the revised draft\n"
            "3. Strengthen weak areas while preserving strong elements\n"
            "4. Return revised draft"
        ),
    }
