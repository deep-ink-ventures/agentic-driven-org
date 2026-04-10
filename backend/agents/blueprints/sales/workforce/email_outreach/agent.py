from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.email_outreach.commands import send_outreach

logger = logging.getLogger(__name__)

SEND_EMAIL_TOOL = {
    "name": "send_email",
    "description": (
        "Send a single outreach email via SendGrid. Call this once per recipient. "
        "The system handles SendGrid API, BCC to the human closer, and delivery logging. "
        "Do NOT include signature or Calendly link in the body — those are appended automatically."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "to_email": {"type": "string", "description": "Recipient email address"},
            "to_name": {"type": "string", "description": "Recipient full name"},
            "subject": {"type": "string", "description": "Person-specific subject line"},
            "body": {"type": "string", "description": "Plain text email body (no signature, no Calendly)"},
        },
        "required": ["to_email", "to_name", "subject", "body"],
    },
}

BRIEFING_TOOL = {
    "name": "prospect_briefing",
    "description": (
        "Generate a briefing for the human closer about this prospect. " "Called once per recipient, after sending."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "prospect_name": {"type": "string"},
            "prospect_company": {"type": "string"},
            "prospect_role": {"type": "string"},
            "why_reaching_out": {"type": "string", "description": "1-2 sentences: why this person, why now"},
            "key_talking_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 talking points for when they book a meeting",
            },
            "what_they_care_about": {"type": "string"},
            "pitch_angle_used": {"type": "string"},
        },
        "required": [
            "prospect_name",
            "prospect_company",
            "prospect_role",
            "why_reaching_out",
            "key_talking_points",
            "what_they_care_about",
            "pitch_angle_used",
        ],
    },
}


class EmailOutreachBlueprint(WorkforceBlueprint):
    name = "Email Outreach"
    slug = "email_outreach"
    description = (
        "Email delivery specialist — sends personalized pitches via SendGrid with Calendly link, "
        "BCC to human closer, and per-prospect briefings"
    )
    tags = ["outreach", "email", "delivery", "sendgrid"]
    skills = [
        {
            "name": "Email Formatting",
            "description": (
                "Format pitch payloads as professional plain text emails. "
                "No HTML, no markdown — just clean text that looks human-written."
            ),
        },
        {
            "name": "Prospect Briefing",
            "description": (
                "Generate concise briefings for the human closer — who this person is, "
                "why we reached out, key talking points for when they book a meeting."
            ),
        },
    ]
    config_schema = {
        "sendgrid_api_key": {
            "type": "str",
            "required": True,
            "description": "SendGrid API key for sending emails",
            "label": "SendGrid API Key",
        },
        "from_email": {
            "type": "email",
            "required": True,
            "description": "Sender email address (must be verified in SendGrid)",
            "label": "From Email",
        },
        "from_name": {
            "type": "str",
            "required": True,
            "description": "Sender display name",
            "label": "From Name",
        },
        "calendly_link": {
            "type": "str",
            "required": True,
            "description": "Calendly (or similar) booking link appended to every email",
            "label": "Calendly Link",
        },
        "bcc_email": {
            "type": "email",
            "required": True,
            "description": "Human closer email — BCC'd on every outreach, receives briefings",
            "label": "BCC Email (Closer)",
        },
        "bcc_name": {
            "type": "str",
            "description": "Human closer name — used in briefing headers",
            "label": "Closer Name",
        },
        "sender_title": {
            "type": "str",
            "description": "Title/role for email signature",
            "label": "Sender Title",
        },
    }

    @property
    def system_prompt(self) -> str:
        return """You are an email outreach delivery agent. You take personalized pitch payloads and send them via the send_email tool.

The pitch content has been written and QA-approved. Do NOT rewrite substantially — format as clean plain text and send.

## Tools

### send_email
Call once per recipient. Provide to_email, to_name, subject, body.
Do NOT include signature or Calendly link in the body — appended automatically.

### prospect_briefing
Call once per recipient AFTER sending. Generates a briefing for the human closer
who is BCC'd on every email. When the prospect books a meeting, the closer has context.

## Workflow Per Recipient
1. Format the pitch as plain text body
2. Call send_email
3. Call prospect_briefing
4. Move to next recipient

After all sends, summarize results in your final response."""

    send_outreach = send_outreach

    def get_task_suffix(self, agent, task):
        config = agent.config or {}
        from_name = config.get("from_name", "")
        sender_title = config.get("sender_title", "")
        calendly = config.get("calendly_link", "")
        bcc_name = config.get("bcc_name", "the closer")

        return (
            f"# EMAIL DELIVERY CONTEXT\n\n"
            f"## Signature (auto-appended — do NOT include in body)\n"
            f"{from_name}\n{sender_title}\n\n"
            f"Book a time: {calendly}\n\n"
            f"## BCC\nEvery email is BCC'd to {bcc_name}. After each send, call prospect_briefing "
            f"so {bcc_name} has context when the prospect responds or books a meeting.\n\n"
            f"## Rules\n"
            f"- Subject line must be person-specific\n"
            f"- Body must be plain text, no markdown\n"
            f"- Do NOT include signature or Calendly link in the body"
        )

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        """Send emails via SendGrid using multi-turn tool loop."""
        from agents.ai.claude_client import call_claude_tool_loop

        config = agent.config or {}
        api_key = config.get("sendgrid_api_key")
        from_email = config.get("from_email")
        from_name = config.get("from_name", "")
        calendly_link = config.get("calendly_link", "")
        bcc_email = config.get("bcc_email")
        sender_title = config.get("sender_title", "")

        if not api_key or not from_email:
            return "ERROR: sendgrid_api_key and from_email must be configured on this agent."

        # Build signature block
        sig_parts = [f"\n\n---\n{from_name}"]
        if sender_title:
            sig_parts.append(sender_title)
        if calendly_link:
            sig_parts.append(f"\nBook a time: {calendly_link}")
        signature = "\n".join(sig_parts)

        delivery_log = []
        briefings = []

        def handle_tool(name: str, tool_input: dict) -> str:
            if name == "send_email":
                result = self._send_via_sendgrid(
                    api_key=api_key,
                    from_email=from_email,
                    from_name=from_name,
                    to_email=tool_input["to_email"],
                    to_name=tool_input["to_name"],
                    subject=tool_input["subject"],
                    body=tool_input["body"] + signature,
                    bcc_email=bcc_email,
                )
                delivery_log.append(result)
                return json.dumps(result)

            if name == "prospect_briefing":
                briefings.append(tool_input)
                return json.dumps({"saved": True})

            return json.dumps({"error": f"Unknown tool: {name}"})

        suffix = self.get_task_suffix(agent, task)
        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude_tool_loop(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            tools=[SEND_EMAIL_TOOL, BRIEFING_TOOL],
            handle_tool_call=handle_tool,
            model=self.get_model(agent, task.command_name),
        )

        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        # Store briefings on agent for later retrieval
        internal_state = agent.internal_state or {}
        stored = internal_state.get("briefings", [])
        stored.extend(briefings)
        internal_state["briefings"] = stored[-100:]  # keep last 100
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        # Build delivery report
        sent = sum(1 for d in delivery_log if d.get("success"))
        failed = len(delivery_log) - sent

        lines = ["# Email Outreach — Delivery Report\n"]
        lines.append(f"**Total:** {sent} sent, {failed} failed\n")
        lines.append("| Recipient | Subject | Status |")
        lines.append("|-----------|---------|--------|")
        for d in delivery_log:
            status = "sent" if d.get("success") else f"failed: {d.get('error', 'unknown')}"
            lines.append(f"| {d.get('to_name', '')} <{d.get('to_email', '')}> | {d.get('subject', '')} | {status} |")

        if briefings:
            lines.append(f"\n**Briefings generated:** {len(briefings)} for {config.get('bcc_name', 'closer')}")

        return "\n".join(lines)

    def _send_via_sendgrid(
        self,
        api_key: str,
        from_email: str,
        from_name: str,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        bcc_email: str | None,
    ) -> dict:
        from integrations.sendgrid.service import send_email

        result = send_email(
            api_key=api_key,
            from_email=from_email,
            from_name=from_name,
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            plain_text_body=body,
            bcc_email=bcc_email,
        )
        result["to_email"] = to_email
        result["to_name"] = to_name
        result["subject"] = subject
        return result
