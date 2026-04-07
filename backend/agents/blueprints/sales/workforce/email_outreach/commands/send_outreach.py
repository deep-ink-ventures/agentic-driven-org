"""Email Outreach command: format and send personalized emails."""

from agents.blueprints.base import command


@command(
    name="send-outreach",
    description=(
        "Take personalized pitch payloads, format as plain text emails, " "and send via configured email channel."
    ),
    model="claude-opus-4-6",
)
def send_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Format and send personalized outreach emails",
        "step_plan": (
            "1. Review the personalized pitch payloads assigned to email outreach\n"
            "2. Format each pitch as a plain text email with subject line\n"
            "3. Verify all emails follow style guidelines (plain text, no markdown)\n"
            "4. Send each email via configured channel\n"
            "5. Log what was sent to whom with timestamps"
        ),
    }
