from agents.blueprints.base import command


@command(
    name="send-campaign",
    description=(
        "Execute a previously approved email campaign via SendGrid after running a full safety checklist: "
        "verify human approval, enforce the minimum 3-day gap between campaigns to the same list, confirm "
        "weekly send limits are not exceeded, and validate the unsubscribe link is present. Monitors initial "
        "deliverability signals post-send and updates internal_state with timestamps and send counts."
    ),
    schedule=None,
)
def send_campaign(self, agent) -> dict:
    return {
        "exec_summary": "Send an approved email campaign via SendGrid to the designated mailing list",
        "step_plan": (
            "1. Verify campaign has been explicitly approved by a human\n"
            "2. Check last_campaign_sent_at — enforce minimum 3-day gap to same list\n"
            "3. Check emails_sent_this_week against weekly limits\n"
            "4. Confirm unsubscribe link is present in email body\n"
            "5. Send campaign via integrations.sendgrid.service.send_campaign()\n"
            "6. Update internal_state: last_campaign_sent_at, emails_sent_this_week\n"
            "7. Log send confirmation and initial delivery stats"
        ),
    }
