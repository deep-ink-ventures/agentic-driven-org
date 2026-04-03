"""
Google Drive service via Google Workspace API.
Secrets are read from ProjectConfig.google_credentials.
"""

import logging

logger = logging.getLogger(__name__)


def _get_config(project):
    config = project.config
    if not config or not config.google_email:
        return None, None
    return config.google_email, config.google_credentials


def list_files(project, folder_id: str = "root", max_results: int = 20) -> dict:
    email, credentials = _get_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}
    logger.info("GDrive list: account=%s folder=%s", email, folder_id)
    return {"success": True, "files": []}


def upload_file(project, name: str, content: bytes, folder_id: str = "root") -> dict:
    email, credentials = _get_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}
    logger.info("GDrive upload: account=%s name=%s folder=%s", email, name, folder_id)
    return {"success": True, "file_id": "stub"}
