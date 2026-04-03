"""
Google services integration.

A shared service for interacting with Google APIs (Gmail, Drive, etc.)
on behalf of a project's configured Google account. Agents access this
through their project's config: agent.department.project.config

Requires google_email and google_credentials on the ProjectConfig.
"""

import logging

logger = logging.getLogger(__name__)


def get_google_config(project):
    """Get Google config from a project. Returns (email, credentials) or (None, None)."""
    config = project.config
    if not config or not config.google_email:
        return None, None
    return config.google_email, config.google_credentials


def send_email(project, to: str, subject: str, body: str) -> dict:
    """
    Send an email via Gmail on behalf of the project's configured Google account.

    Args:
        project: Project instance (must have config with google_email + credentials)
        to: Recipient email
        subject: Email subject
        body: Email body (plain text)

    Returns:
        dict with "success" bool and "message_id" or "error"
    """
    email, credentials = get_google_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}

    logger.info("Would send email from %s to %s: %s", email, to, subject[:50])

    # Stub: actual implementation will use Google Gmail API with OAuth credentials
    return {
        "success": True,
        "message_id": "stub",
        "from": email,
        "to": to,
        "subject": subject,
    }


def read_emails(project, query: str = "", max_results: int = 10) -> dict:
    """
    Read emails from the project's configured Gmail account.

    Args:
        project: Project instance
        query: Gmail search query (e.g. "is:unread", "from:someone@example.com")
        max_results: Max emails to return

    Returns:
        dict with "success" bool and "emails" list or "error"
    """
    email, credentials = get_google_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}

    logger.info("Would read emails for %s, query='%s'", email, query)

    # Stub: actual implementation will use Google Gmail API
    return {
        "success": True,
        "emails": [],
    }


def list_drive_files(project, folder_id: str = "root", max_results: int = 20) -> dict:
    """
    List files in the project's configured Google Drive.

    Args:
        project: Project instance
        folder_id: Drive folder ID (default: root)
        max_results: Max files to return

    Returns:
        dict with "success" bool and "files" list or "error"
    """
    email, credentials = get_google_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}

    logger.info("Would list Drive files for %s in folder %s", email, folder_id)

    # Stub: actual implementation will use Google Drive API
    return {
        "success": True,
        "files": [],
    }
