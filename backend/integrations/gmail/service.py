"""
Gmail service via Google Workspace API.
Secrets are read from ProjectConfig.google_credentials.
"""

import logging

logger = logging.getLogger(__name__)


def _get_config(project):
    config = project.config
    if not config or not config.google_email:
        return None, None
    return config.google_email, config.google_credentials


def send_email(project, to: str, subject: str, body: str) -> dict:
    email, credentials = _get_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}
    logger.info("Gmail send: from=%s to=%s subject='%s'", email, to, subject[:50])
    return {"success": True, "message_id": "stub", "from": email, "to": to}


def read_emails(project, query: str = "", max_results: int = 10) -> dict:
    email, credentials = _get_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}
    logger.info("Gmail read: account=%s query='%s'", email, query)
    return {"success": True, "emails": []}
