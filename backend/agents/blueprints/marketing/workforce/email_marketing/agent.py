from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.marketing.workforce.email_marketing.skills import format_skills
from agents.blueprints.marketing.workforce.email_marketing.commands import (
    check_campaign_performance,
    draft_campaign,
    send_campaign,
)

logger = logging.getLogger(__name__)


class EmailMarketingBlueprint(WorkforceBlueprint):
    name = "Email Marketing Specialist"
    slug = "email_marketing"
    description = "Designs and sends email campaigns via SendGrid with strict approval gates"
    tags = ["email", "campaigns", "outreach", "nurture"]
    config_schema = {
        "sendgrid_api_key": {"type": "str", "required": True, "label": "SendGrid API Key", "description": "Your SendGrid API key for sending emails"},
        "default_from_email": {"type": "str", "required": True, "label": "Sender Email", "description": "Default sender email address for campaigns"},
        "mailing_lists": {"type": "dict", "required": True, "label": "Mailing Lists", "description": "Mailing list name → SendGrid list ID mapping"},
    }

    @property
    def system_prompt(self) -> str:
        return """You are an email marketing specialist agent. You design, draft, and send email campaigns via SendGrid. You follow strict safety rules and email marketing best practices to protect brand reputation and ensure compliance.

## EMAIL SAFETY RULES — NON-NEGOTIABLE:
- NEVER send emails without explicit human approval
- Draft commands ALWAYS create tasks in awaiting_approval status
- Track last_campaign_sent_at in internal_state — minimum 3 days between campaigns to same list
- Track emails_sent_this_week in internal_state
- All campaigns MUST include unsubscribe link
- Subject lines MUST include 2-3 A/B options
- Optimal send times: Tuesday/Thursday 10am local time

## Email Marketing Best Practices:
- Write concise, benefit-driven subject lines (40-60 characters)
- Personalize content where possible using merge tags
- Keep email body scannable: short paragraphs, bullet points, clear CTA
- Mobile-first design — most opens happen on mobile
- Preview text should complement (not repeat) the subject line
- Segment audiences for relevance — never blast entire list without reason
- Monitor deliverability: keep bounce rate under 2%, unsubscribe under 0.5%
- Respect CAN-SPAM / GDPR requirements at all times

When executing tasks, respond with a JSON object:
{
    "campaign": {
        "subject_lines": ["Option A", "Option B", "Option C"],
        "body_preview": "First 100 chars of email body...",
        "target_list": "list name or segment",
        "send_time": "recommended send time",
        "has_unsubscribe": true
    },
    "report": "Summary of what was done and key metrics"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    check_campaign_performance = check_campaign_performance
    draft_campaign = draft_campaign
    send_campaign = send_campaign

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        config = agent.config or {}
        internal_state = agent.internal_state or {}
        task_summary = (task.exec_summary or "").lower()

        # --- Draft tasks: generate email content via Claude ---
        if "draft" in task_summary or task.status == "awaiting_approval":
            suffix = (
                "You are drafting an email campaign. Generate compelling content with "
                "2-3 A/B subject line options, email body with unsubscribe link, and "
                "recommended send time. This is a DRAFT — it will NOT be sent without "
                "human approval.\n\n"
                f"Available mailing lists: {json.dumps(config.get('mailing_lists', {}))}\n"
                f"Default from email: {config.get('default_from_email', 'not configured')}"
            )

            task_msg = self.build_task_message(agent, task, suffix=suffix)

            response, usage = call_claude(
                system_prompt=self.build_system_prompt(agent),
                user_message=task_msg,
                model=self.get_model(agent),
            )
            task.token_usage = usage
            task.save(update_fields=["token_usage"])

            # Ensure the task stays in awaiting_approval
            task.status = "awaiting_approval"
            task.save(update_fields=["status"])

            try:
                data = json.loads(response)
                return data.get("report", response)
            except (json.JSONDecodeError, KeyError):
                return response

        # --- Send tasks: execute approved campaign via SendGrid ---
        if "send" in task_summary:
            from integrations.sendgrid.service import send_campaign as sg_send

            # Safety check: minimum 3-day gap
            import datetime

            last_sent = internal_state.get("last_campaign_sent_at")
            if last_sent:
                last_dt = datetime.datetime.fromisoformat(last_sent)
                now = datetime.datetime.now(tz=datetime.timezone.utc)
                if (now - last_dt).days < 3:
                    return json.dumps({
                        "error": "Campaign blocked: minimum 3-day gap between campaigns not met",
                        "last_sent": last_sent,
                        "report": "Send blocked — last campaign was sent less than 3 days ago.",
                    })

            # Execute send
            result = sg_send(
                api_key=config.get("sendgrid_api_key", ""),
                from_email=config.get("default_from_email", ""),
                task=task,
            )

            # Update internal_state timestamps
            now_iso = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
            internal_state["last_campaign_sent_at"] = now_iso
            internal_state["emails_sent_this_week"] = internal_state.get("emails_sent_this_week", 0) + 1
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])

            return json.dumps({
                "campaign": result,
                "report": f"Campaign sent successfully at {now_iso}.",
            })

        # --- Default: performance check or general tasks via Claude ---
        suffix = (
            "Analyze the email campaign data and provide actionable insights.\n\n"
            f"SendGrid API key configured: {'yes' if config.get('sendgrid_api_key') else 'no'}\n"
            f"Internal state: {json.dumps(internal_state)}"
        )

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        try:
            data = json.loads(response)
            return data.get("report", response)
        except (json.JSONDecodeError, KeyError):
            return response
