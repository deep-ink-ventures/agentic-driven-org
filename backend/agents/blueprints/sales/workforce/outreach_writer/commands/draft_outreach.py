"""Outreach writer command: draft personalized outreach."""

from agents.blueprints.base import command


@command(
    name="draft-outreach",
    description=(
        "Write personalized outreach for a specific prospect. Uses prospect research and project "
        "positioning to produce an email or message draft with subject line, body, and call to action."
    ),
    model="claude-sonnet-4-6",
)
def draft_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Draft personalized outreach for a qualified prospect",
        "step_plan": (
            "1. Review prospect research and qualification notes\n"
            "2. Identify the strongest angle for outreach\n"
            "3. Draft subject line, body, and CTA\n"
            "4. Ensure personalization references specific prospect details"
        ),
    }
