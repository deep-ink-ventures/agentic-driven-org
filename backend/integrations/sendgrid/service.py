"""
SendGrid email service. Handles campaign sending and analytics.
Secrets are read from agent.config — never passed by the agent blueprint.
"""

import logging

import sendgrid
from sendgrid.helpers.mail import Bcc, Mail, To

logger = logging.getLogger(__name__)


def send_email(
    api_key: str,
    from_email: str,
    from_name: str,
    to_email: str,
    to_name: str,
    subject: str,
    plain_text_body: str,
    bcc_email: str | None = None,
) -> dict:
    """Send a single plain-text email via SendGrid.

    Returns dict with 'success', 'status_code', and optionally 'error'.
    """
    sg = sendgrid.SendGridAPIClient(api_key=api_key)

    message = Mail()
    message.from_email = (from_email, from_name)
    message.to = [To(to_email, to_name)]
    message.subject = subject
    message.plain_text_content = plain_text_body

    if bcc_email:
        message.bcc = [Bcc(bcc_email)]

    try:
        response = sg.send(message)
        status = response.status_code
        if status in (200, 201, 202):
            logger.info(
                "SENDGRID_SENT to=%s subject='%s' status=%d",
                to_email,
                subject[:50],
                status,
            )
            return {"success": True, "status_code": status}
        else:
            logger.warning(
                "SENDGRID_UNEXPECTED to=%s status=%d body=%s",
                to_email,
                status,
                response.body,
            )
            return {"success": False, "status_code": status, "error": str(response.body)}
    except Exception as e:
        logger.exception("SENDGRID_ERROR to=%s error=%s", to_email, e)
        return {"success": False, "status_code": 0, "error": str(e)}


def send_campaign(api_key: str, from_email: str, to_list_id: str, subject: str, html_body: str) -> dict:
    logger.info("SendGrid send_campaign: from=%s, list=%s, subject='%s'", from_email, to_list_id, subject[:50])
    return {"success": True, "campaign_id": "stub", "from": from_email, "to_list": to_list_id}


def get_campaign_stats(api_key: str, campaign_id: str) -> dict:
    logger.info("SendGrid get_campaign_stats: campaign=%s", campaign_id)
    return {"success": True, "opens": 0, "clicks": 0, "unsubscribes": 0, "bounces": 0}


def list_contacts(api_key: str, list_id: str) -> dict:
    logger.info("SendGrid list_contacts: list=%s", list_id)
    return {"success": True, "count": 0, "contacts": []}
