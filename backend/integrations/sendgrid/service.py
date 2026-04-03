"""
SendGrid email service. Handles campaign sending and analytics.
Secrets are read from agent.config — never passed by the agent blueprint.
"""

import logging

logger = logging.getLogger(__name__)


def send_campaign(api_key: str, from_email: str, to_list_id: str, subject: str, html_body: str) -> dict:
    logger.info("SendGrid send_campaign: from=%s, list=%s, subject='%s'", from_email, to_list_id, subject[:50])
    return {"success": True, "campaign_id": "stub", "from": from_email, "to_list": to_list_id}


def get_campaign_stats(api_key: str, campaign_id: str) -> dict:
    logger.info("SendGrid get_campaign_stats: campaign=%s", campaign_id)
    return {"success": True, "opens": 0, "clicks": 0, "unsubscribes": 0, "bounces": 0}


def list_contacts(api_key: str, list_id: str) -> dict:
    logger.info("SendGrid list_contacts: list=%s", list_id)
    return {"success": True, "count": 0, "contacts": []}
