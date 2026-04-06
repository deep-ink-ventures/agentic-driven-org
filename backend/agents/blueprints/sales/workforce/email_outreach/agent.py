from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.email_outreach.commands import send_outreach

logger = logging.getLogger(__name__)


class EmailOutreachBlueprint(WorkforceBlueprint):
    name = "Email Outreach"
    slug = "email_outreach"
    description = (
        "Email delivery specialist — formats personalized pitch payloads as plain text emails "
        "and sends via configured email channel"
    )
    tags = ["outreach", "email", "delivery", "sending"]
    skills = [
        {
            "name": "Email Formatting",
            "description": (
                "Format pitch payloads as professional plain text emails. "
                "No HTML, no markdown, no formatting — just clean text that looks human-written."
            ),
        },
        {
            "name": "Delivery Management",
            "description": (
                "Send emails via configured channel, log delivery status, "
                "handle errors gracefully, report what was sent to whom."
            ),
        },
    ]
    config_schema = {
        "sender_name": {
            "type": "str",
            "description": "Name to display as email sender",
            "label": "Sender Name",
        },
        "sender_title": {
            "type": "str",
            "description": "Title/role for email signature",
            "label": "Sender Title",
        },
    }

    @property
    def system_prompt(self) -> str:
        return """You are an email outreach delivery agent. You take personalized pitch payloads and send them as emails.

Your job is formatting and delivery — the pitch content has already been written and QA-approved. Do NOT rewrite the pitches. Format them as clean plain text emails and send.

## Email Format Rules
- Plain text ONLY — no HTML, no markdown, no bullet points, no bold/italic
- Subject line: use the one from the pitch payload exactly
- Body: the pitch text, followed by a simple signature
- Signature: [sender_name] / [sender_title] (from your config)
- No images, no links (unless specifically in the pitch payload), no tracking pixels
- Line length: wrap at 72 characters for readability

## Sending Rules
- Send one email at a time, not bulk
- Log each send: recipient, subject, timestamp, status
- If sending fails, log the error and continue with remaining emails
- Never modify the pitch content — you are a delivery agent, not an editor

## Report Format
After sending, produce a delivery report:

| Recipient | Subject | Status | Timestamp |
|-----------|---------|--------|-----------|
| name@email | Subject line | sent/failed | ISO timestamp |

Total: X sent, Y failed

If any sends failed, include error details."""

    send_outreach = send_outreach

    def get_task_suffix(self, agent, task):
        return """# EMAIL DELIVERY METHODOLOGY

## Pre-Send Checklist
- Verify each pitch payload has: recipient name, email, subject, body
- Verify subject line is person-specific (not a generic campaign subject)
- Verify body is plain text (no markdown artifacts like ** or ## or - bullets)
- Verify body is under 200 words
- Verify signature is properly formatted

## Sending
- Use the configured email channel (Gmail API, SendGrid, etc.)
- Send one at a time with a brief pause between sends
- Capture delivery status for each email

## Post-Send
- Produce the delivery report table
- Flag any emails that bounced or failed
- Note any recipients where email address was missing or invalid"""
