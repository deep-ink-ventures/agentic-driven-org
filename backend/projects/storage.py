"""
File storage abstraction. Local filesystem in dev, GCS in production.

Controlled by STORAGE_BACKEND setting:
  - "local" (default when DEBUG=True): files in MEDIA_ROOT, served via Django
  - "gcs": Google Cloud Storage with signed URLs
"""

import logging
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

STORAGE_BACKEND = getattr(settings, "STORAGE_BACKEND", "local")

# ── Local filesystem backend ─────────────────────────────────────────────────

LOCAL_MEDIA_ROOT = Path(getattr(settings, "MEDIA_ROOT", settings.BASE_DIR / "media"))


def _local_upload(content: bytes, filename: str, project_id: str, subfolder: str) -> str:
    file_id = uuid.uuid4().hex[:8]
    rel_path = f"projects/{project_id}/{subfolder}/{file_id}_{filename}"
    full_path = LOCAL_MEDIA_ROOT / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)
    logger.info("Stored %s (%d bytes) at %s", filename, len(content), full_path)
    return rel_path


def _local_get_url(blob_path: str) -> str:
    if not blob_path:
        return ""
    return f"/media/{blob_path}"


def _local_delete(blob_path: str) -> bool:
    if not blob_path:
        return False
    full_path = LOCAL_MEDIA_ROOT / blob_path
    if full_path.exists():
        full_path.unlink()
        logger.info("Deleted %s", full_path)
        return True
    return False


def _local_delete_project(project_id: str) -> int:
    import shutil

    project_dir = LOCAL_MEDIA_ROOT / "projects" / project_id
    if project_dir.exists():
        count = sum(1 for _ in project_dir.rglob("*") if _.is_file())
        shutil.rmtree(project_dir)
        logger.info("Deleted %d files for project %s", count, project_id)
        return count
    return 0


# ── GCS backend ──────────────────────────────────────────────────────────────

GCS_BUCKET = getattr(settings, "GCS_BUCKET", "agentic-company-uploads")
SIGNED_URL_EXPIRY = timedelta(hours=1)


def _get_gcs_client():
    from google.cloud import storage as gcs

    return gcs.Client(project=getattr(settings, "GCP_PROJECT_ID", ""))


def _gcs_upload(content: bytes, filename: str, project_id: str, subfolder: str) -> str:
    try:
        client = _get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        file_id = uuid.uuid4().hex[:8]
        blob_path = f"projects/{project_id}/{subfolder}/{file_id}_{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(content, content_type=_guess_content_type(filename))
        logger.info("Uploaded %s (%d bytes) to gs://%s/%s", filename, len(content), GCS_BUCKET, blob_path)
        return blob_path
    except Exception as e:
        logger.error("GCS upload failed: %s", e)
        return ""


def _gcs_get_url(blob_path: str) -> str:
    if not blob_path:
        return ""
    try:
        import google.auth
        from google.auth.transport import requests as auth_requests

        client = _get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)

        credentials, project = google.auth.default()
        if hasattr(credentials, "service_account_email"):
            auth_req = auth_requests.Request()
            credentials.refresh(auth_req)
            sa_email = credentials.service_account_email
            if not sa_email or sa_email == "default":
                import requests as _requests

                sa_email = _requests.get(
                    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
                    headers={"Metadata-Flavor": "Google"},
                    timeout=2,
                ).text
            return blob.generate_signed_url(
                version="v4",
                expiration=SIGNED_URL_EXPIRY,
                method="GET",
                service_account_email=sa_email,
                access_token=credentials.token,
            )
        else:
            return blob.generate_signed_url(version="v4", expiration=SIGNED_URL_EXPIRY, method="GET")
    except Exception as e:
        logger.error("Failed to generate signed URL for %s: %s", blob_path, e)
        return ""


def _gcs_delete(blob_path: str) -> bool:
    if not blob_path:
        return False
    try:
        client = _get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        blob.delete()
        logger.info("Deleted gs://%s/%s", GCS_BUCKET, blob_path)
        return True
    except Exception as e:
        logger.error("Failed to delete %s: %s", blob_path, e)
        return False


def _gcs_delete_project(project_id: str) -> int:
    try:
        client = _get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        prefix = f"projects/{project_id}/"
        blobs = list(bucket.list_blobs(prefix=prefix))
        for blob in blobs:
            blob.delete()
        logger.info("Deleted %d files for project %s", len(blobs), project_id)
        return len(blobs)
    except Exception as e:
        logger.error("Failed to delete project files %s: %s", project_id, e)
        return 0


# ── Public API ───────────────────────────────────────────────────────────────


def upload_file(content: bytes, filename: str, project_id: str, subfolder: str = "sources") -> str:
    if STORAGE_BACKEND == "local":
        return _local_upload(content, filename, project_id, subfolder)
    return _gcs_upload(content, filename, project_id, subfolder)


def get_signed_url(blob_path: str) -> str:
    if STORAGE_BACKEND == "local":
        return _local_get_url(blob_path)
    return _gcs_get_url(blob_path)


def delete_file(blob_path: str) -> bool:
    if STORAGE_BACKEND == "local":
        return _local_delete(blob_path)
    return _gcs_delete(blob_path)


def delete_project_files(project_id: str) -> int:
    if STORAGE_BACKEND == "local":
        return _local_delete_project(project_id)
    return _gcs_delete_project(project_id)


def _guess_content_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "md": "text/plain",
    }.get(ext, "application/octet-stream")
