# Sources & Auto-Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add source material upload and Claude-powered auto-bootstrap that analyzes sources and proposes departments, agents, and documents for a project.

**Architecture:** Source model on Project stores files/URLs/text with extracted text. BootstrapProposal model tracks bootstrap attempts. A Celery task sends source content to Claude, which returns a structured JSON proposal. Admin actions trigger bootstrap and approve proposals.

**Tech Stack:** Django, Celery, PyMuPDF, python-docx, BeautifulSoup, Claude API (via existing agents.ai.claude_client)

---

## File Structure

```
backend/
├── projects/
│   ├── models/
│   │   ├── source.py                     (create)
│   │   ├── bootstrap_proposal.py         (create)
│   │   └── __init__.py                   (modify — add exports)
│   ├── admin/
│   │   ├── source_admin.py               (create)
│   │   ├── bootstrap_proposal_admin.py   (create)
│   │   ├── project_admin.py              (modify — add bootstrap action + source inline)
│   │   └── __init__.py                   (modify — add exports)
│   ├── storage.py                        (create)
│   ├── extraction.py                     (create)
│   ├── prompts.py                        (create)
│   └── tasks.py                          (create)
├── requirements.txt                      (modify — add new deps)
└── config/
    └── settings.py                       (modify — add MEDIA_ROOT, CELERY_BEAT entry)
```

---

### Task 1: Dependencies & Settings

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/config/settings.py`

- [ ] **Step 1: Add new dependencies to requirements.txt**

Add these lines to `backend/requirements.txt` after the `whitenoise` line:

```
pymupdf>=1.25,<2.0
python-docx>=1.1,<2.0
beautifulsoup4>=4.12,<5.0
lxml>=5.0,<6.0
```

- [ ] **Step 2: Install new dependencies**

Run:
```bash
cd backend && source venv/bin/activate && pip install -r requirements.txt
```

- [ ] **Step 3: Add MEDIA settings to config/settings.py**

Add after the `STATIC_ROOT` line in `backend/config/settings.py`:

```python
# Media files (local storage backend for dev)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Storage backend — "local" in dev, "gcs" in production
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local" if DEBUG else "gcs")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "agentic-company-uploads")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
```

- [ ] **Step 4: Serve media files in dev — update config/urls.py**

Add to `backend/config/urls.py`:

```python
from django.conf import settings
from django.conf.urls.static import static

# at the end of the file, after urlpatterns:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/config/settings.py backend/config/urls.py
git commit -m "feat: add extraction dependencies and media/storage settings"
```

---

### Task 2: Storage Abstraction

**Files:**
- Create: `backend/projects/storage.py`

- [ ] **Step 1: Create projects/storage.py**

Lifted from scriptpulse, adapted for this project. The `subfolder` parameter replaces scriptpulse's `stage_type`.

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/projects/storage.py
git commit -m "feat: file storage abstraction (local + GCS dual backend)"
```

---

### Task 3: Text Extraction

**Files:**
- Create: `backend/projects/extraction.py`

- [ ] **Step 1: Create projects/extraction.py**

```python
"""
Text extraction from various source types.

Each extractor is memory-efficient: processes page-at-a-time,
closes handles promptly, and avoids loading entire files into memory.
"""

import hashlib
import logging

logger = logging.getLogger(__name__)

MAX_URL_SIZE = 5 * 1024 * 1024  # 5MB max for URL fetch
URL_TIMEOUT = 15  # seconds


def extract_from_pdf(content: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF. Page-at-a-time for memory efficiency."""
    import fitz

    text_parts = []
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        for page in doc:
            text_parts.append(page.get_text())
    finally:
        doc.close()
    return "\n\n".join(text_parts)


def extract_from_docx(content: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    import io

    from docx import Document

    doc = Document(io.BytesIO(content))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_from_txt(content: bytes) -> str:
    """Extract text from plain text / markdown bytes."""
    for encoding in ("utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def extract_from_url(url: str) -> str:
    """Fetch URL and extract main text content. Strips nav, footer, scripts."""
    import requests
    from bs4 import BeautifulSoup

    response = requests.get(
        url,
        timeout=URL_TIMEOUT,
        headers={"User-Agent": "AgenticCompany/1.0"},
        stream=True,
    )
    response.raise_for_status()

    # Read up to max size
    chunks = []
    size = 0
    for chunk in response.iter_content(chunk_size=8192):
        chunks.append(chunk)
        size += len(chunk)
        if size > MAX_URL_SIZE:
            break
    html = b"".join(chunks)

    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
        tag.decompose()

    # Try to find main content area
    main = soup.find("main") or soup.find("article") or soup.find("body")
    if main is None:
        main = soup

    text = main.get_text(separator="\n", strip=True)
    # Collapse multiple blank lines
    lines = [line for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def extract_text(source) -> str:
    """
    Extract text from a Source model instance.
    Dispatches to the right extractor based on source_type and file_format.

    Returns extracted text string.
    """
    if source.source_type == "text":
        return source.raw_content or ""

    if source.source_type == "url":
        if not source.url:
            return ""
        try:
            return extract_from_url(source.url)
        except Exception as e:
            logger.exception("Failed to extract from URL %s: %s", source.url, e)
            return f"[Extraction failed: {e}]"

    if source.source_type == "file":
        if not source.file_key:
            return ""

        # Read file content from storage
        from projects.storage import LOCAL_MEDIA_ROOT, STORAGE_BACKEND

        if STORAGE_BACKEND == "local":
            file_path = LOCAL_MEDIA_ROOT / source.file_key
            if not file_path.exists():
                return "[File not found]"
            content = file_path.read_bytes()
        else:
            from google.cloud import storage as gcs
            from django.conf import settings

            client = gcs.Client(project=settings.GCP_PROJECT_ID)
            bucket = client.bucket(settings.GCS_BUCKET)
            blob = bucket.blob(source.file_key)
            content = blob.download_as_bytes()

        fmt = (source.file_format or "").lower()
        try:
            if fmt == "pdf":
                return extract_from_pdf(content)
            elif fmt == "docx":
                return extract_from_docx(content)
            elif fmt in ("txt", "md", "markdown"):
                return extract_from_txt(content)
            else:
                return extract_from_txt(content)  # fallback: try as text
        except Exception as e:
            logger.exception("Failed to extract from %s: %s", source.original_filename, e)
            return f"[Extraction failed: {e}]"

    return ""


def compute_content_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content for dedup."""
    return hashlib.sha256(content).hexdigest()
```

- [ ] **Step 2: Commit**

```bash
git add backend/projects/extraction.py
git commit -m "feat: text extraction — PDF, DOCX, TXT, URL with memory efficiency"
```

---

### Task 4: Source & BootstrapProposal Models

**Files:**
- Create: `backend/projects/models/source.py`
- Create: `backend/projects/models/bootstrap_proposal.py`
- Modify: `backend/projects/models/__init__.py`

- [ ] **Step 1: Create projects/models/source.py**

```python
import uuid

from django.conf import settings
from django.db import models


class Source(models.Model):
    class SourceType(models.TextChoices):
        FILE = "file", "File"
        URL = "url", "URL"
        TEXT = "text", "Text"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="sources",
    )
    source_type = models.CharField(
        max_length=10,
        choices=SourceType.choices,
        default=SourceType.FILE,
    )
    original_filename = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)
    file_key = models.CharField(
        max_length=512,
        blank=True,
        help_text="Storage path — private, never expose directly.",
    )
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hex digest of file content.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sources",
        null=True,
        blank=True,
    )
    raw_content = models.TextField(
        blank=True,
        help_text="For text sources: the raw text. For files: unprocessed extracted text.",
    )
    extracted_text = models.TextField(
        blank=True,
        help_text="Cleaned text ready for Claude analysis.",
    )
    file_format = models.CharField(max_length=20, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    word_count = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_hash"],
                name="unique_content_per_user",
                condition=models.Q(content_hash__gt=""),
            ),
        ]

    def __str__(self):
        if self.source_type == "file":
            return f"{self.original_filename} — {self.project.name}"
        elif self.source_type == "url":
            return f"{self.url[:60]} — {self.project.name}"
        return f"Text source — {self.project.name}"
```

- [ ] **Step 2: Create projects/models/bootstrap_proposal.py**

```python
import uuid

from django.db import models


class BootstrapProposal(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="bootstrap_proposals",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    proposal = models.JSONField(
        null=True,
        blank=True,
        help_text="The proposed departments, agents, and documents.",
    )
    error_message = models.TextField(blank=True)
    token_usage = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_status_display()}] Bootstrap for {self.project.name}"
```

- [ ] **Step 3: Update projects/models/__init__.py**

Replace the entire file:

```python
from .project import Project
from .department import Department
from .tag import Tag
from .document import Document
from .source import Source
from .bootstrap_proposal import BootstrapProposal

__all__ = ["Project", "Department", "Tag", "Document", "Source", "BootstrapProposal"]
```

- [ ] **Step 4: Run makemigrations and migrate**

Run:
```bash
cd backend && source venv/bin/activate && python manage.py makemigrations projects && python manage.py migrate
```

- [ ] **Step 5: Commit**

```bash
git add backend/projects/models/
git commit -m "feat: Source and BootstrapProposal models with migration"
```

---

### Task 5: Bootstrap Prompt

**Files:**
- Create: `backend/projects/prompts.py`

- [ ] **Step 1: Create projects/prompts.py**

```python
"""
Bootstrap prompt for Claude to analyze project sources and propose setup.
"""


BOOTSTRAP_SYSTEM_PROMPT = """You are a project setup analyst for an AI agent platform. Your job is to analyze source materials provided by a user and propose the optimal configuration of departments, AI agents, and department documents.

You MUST respond with valid JSON matching the exact schema below. No markdown, no explanation outside the JSON.

## Rules

1. Only propose agent types from the AVAILABLE AGENT TYPES list provided. Do not invent new types.
2. Each department should have at least one agent and at least one document.
3. Agent instructions should be specific and derived from the source material — reference the project's domain, audience, tone, and goals.
4. Documents should extract and structure useful information from the sources — branding guidelines, target audience profiles, content strategies, etc.
5. Explain what you extracted from each source and why. If a source wasn't useful, explain why it was ignored.
6. Keep document content in markdown format, actionable and concise.
7. Set campaign agents as needing auto_exec_hourly=false and subordinate agents (twitter, reddit) as auto_exec_hourly=false initially. The user will enable these manually.

## Response JSON Schema

{
    "summary": "2-3 sentence analysis of the project and what was found in the sources",
    "departments": [
        {
            "name": "Department Name",
            "documents": [
                {
                    "title": "Document Title",
                    "content": "Markdown content...",
                    "tags": ["tag1", "tag2"]
                }
            ],
            "agents": [
                {
                    "name": "Human-friendly Agent Name",
                    "agent_type": "one_of_available_types",
                    "instructions": "Specific instructions for this agent derived from sources...",
                    "auto_exec_hourly": false
                }
            ]
        }
    ],
    "ignored_content": [
        {
            "source_id": "uuid-string",
            "source_name": "filename or description",
            "reason": "Why this source was not useful"
        }
    ]
}"""


def build_bootstrap_user_message(
    project_name: str,
    project_goal: str,
    sources: list[dict],
    available_types: list[dict],
) -> str:
    """
    Build the user message for the bootstrap prompt.

    Args:
        project_name: Name of the project
        project_goal: Project goal in markdown
        sources: List of dicts with keys: id, name, source_type, text
        available_types: List of dicts with keys: slug, name, description
    """
    types_text = "\n".join(
        f"- **{t['slug']}** ({t['name']}): {t['description']}"
        for t in available_types
    )

    sources_text = ""
    for s in sources:
        sources_text += f"\n\n### Source: {s['name']} (type: {s['source_type']}, id: {s['id']})\n"
        text = s["text"]
        if len(text) > 10000:
            text = text[:10000] + "\n\n[... truncated ...]"
        sources_text += text

    return f"""# Project: {project_name}

## Goal
{project_goal}

## Available Agent Types
{types_text}

## Source Materials
{sources_text}

Analyze these sources and propose the optimal project setup. Respond with JSON only."""
```

- [ ] **Step 2: Commit**

```bash
git add backend/projects/prompts.py
git commit -m "feat: bootstrap prompt for Claude project analysis"
```

---

### Task 6: Bootstrap Celery Task

**Files:**
- Create: `backend/projects/tasks.py`

- [ ] **Step 1: Create projects/tasks.py**

```python
import json
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def bootstrap_project(self, proposal_id: str):
    """
    Analyze project sources with Claude and generate a bootstrap proposal.
    """
    from projects.models import BootstrapProposal, Source
    from projects.prompts import BOOTSTRAP_SYSTEM_PROMPT, build_bootstrap_user_message
    from agents.ai.claude_client import call_claude
    from agents.blueprints import _REGISTRY

    try:
        proposal = BootstrapProposal.objects.select_related("project").get(id=proposal_id)
    except BootstrapProposal.DoesNotExist:
        logger.error("BootstrapProposal %s not found", proposal_id)
        return

    proposal.status = BootstrapProposal.Status.PROCESSING
    proposal.save(update_fields=["status", "updated_at"])

    project = proposal.project

    try:
        # Gather sources
        sources = Source.objects.filter(project=project)
        if not sources.exists():
            raise ValueError("No sources found for this project")

        source_data = []
        for s in sources:
            text = s.extracted_text or s.raw_content or ""
            if not text:
                continue
            name = s.original_filename or s.url or "Text input"
            source_data.append({
                "id": str(s.id),
                "name": name,
                "source_type": s.source_type,
                "text": text,
            })

        if not source_data:
            raise ValueError("No sources with extracted text found")

        # Available blueprint types
        available_types = [
            {"slug": slug, "name": bp.name, "description": bp.description}
            for slug, bp in _REGISTRY.items()
        ]

        # Build prompt
        user_message = build_bootstrap_user_message(
            project_name=project.name,
            project_goal=project.goal,
            sources=source_data,
            available_types=available_types,
        )

        # Call Claude
        response = call_claude(
            system_prompt=BOOTSTRAP_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=8192,
        )

        # Parse JSON response — strip markdown fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        proposal_data = json.loads(cleaned)

        proposal.proposal = proposal_data
        proposal.status = BootstrapProposal.Status.PROPOSED
        proposal.save(update_fields=["proposal", "status", "updated_at"])

        logger.info("Bootstrap proposal generated for project %s", project.name)

    except Exception as e:
        logger.exception("Bootstrap failed for project %s: %s", project.name, e)
        proposal.status = BootstrapProposal.Status.FAILED
        proposal.error_message = str(e)[:1000]
        proposal.save(update_fields=["status", "error_message", "updated_at"])
```

- [ ] **Step 2: Commit**

```bash
git add backend/projects/tasks.py
git commit -m "feat: bootstrap_project Celery task — analyzes sources with Claude"
```

---

### Task 7: Admin — Source, BootstrapProposal, Project Updates

**Files:**
- Create: `backend/projects/admin/source_admin.py`
- Create: `backend/projects/admin/bootstrap_proposal_admin.py`
- Modify: `backend/projects/admin/project_admin.py`
- Modify: `backend/projects/admin/__init__.py`

- [ ] **Step 1: Create projects/admin/source_admin.py**

```python
import hashlib

from django.contrib import admin

from projects.models import Source
from projects.extraction import extract_text, compute_content_hash
from projects.storage import upload_file


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("source_label", "source_type", "file_format", "file_size", "word_count", "project", "created_at")
    list_filter = ("source_type", "file_format", "project")
    search_fields = ("original_filename", "url", "project__name")
    readonly_fields = ("id", "file_key", "content_hash", "extracted_text", "word_count", "file_size", "created_at")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("id", "project", "source_type", "user")}),
        ("File Source", {"fields": ("original_filename", "file_key", "file_format", "content_type", "file_size", "content_hash")}),
        ("URL Source", {"fields": ("url",)}),
        ("Text Source", {"fields": ("raw_content",)}),
        ("Extraction", {"fields": ("extracted_text", "word_count")}),
        ("Timestamps", {"fields": ("created_at",)}),
    )

    @admin.display(description="Source")
    def source_label(self, obj):
        if obj.source_type == "file":
            return obj.original_filename or "—"
        elif obj.source_type == "url":
            return (obj.url or "—")[:60]
        return "Text input"
```

- [ ] **Step 2: Create projects/admin/bootstrap_proposal_admin.py**

```python
import json
import logging

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from projects.models import BootstrapProposal, Department, Document, Tag
from agents.models import Agent

logger = logging.getLogger(__name__)


@admin.register(BootstrapProposal)
class BootstrapProposalAdmin(admin.ModelAdmin):
    list_display = ("project", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("project__name",)
    readonly_fields = ("id", "project", "proposal_formatted", "token_usage", "error_message", "created_at", "updated_at")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("id", "project", "status")}),
        ("Proposal", {"fields": ("proposal_formatted",)}),
        ("Debug", {"fields": ("error_message", "token_usage")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    actions = ["approve_and_apply", "reject_proposal"]

    @admin.display(description="Proposal (formatted)")
    def proposal_formatted(self, obj):
        if not obj.proposal:
            return "—"
        return format_html("<pre style='max-height:600px;overflow:auto'>{}</pre>", json.dumps(obj.proposal, indent=2))

    @admin.action(description="Approve & Apply — create departments, agents, documents")
    def approve_and_apply(self, request, queryset):
        for proposal in queryset.filter(status=BootstrapProposal.Status.PROPOSED):
            try:
                self._apply_proposal(proposal)
                proposal.status = BootstrapProposal.Status.APPROVED
                proposal.save(update_fields=["status", "updated_at"])
                self.message_user(request, f"Applied bootstrap for {proposal.project.name}")
            except Exception as e:
                logger.exception("Failed to apply bootstrap: %s", e)
                self.message_user(request, f"Failed to apply for {proposal.project.name}: {e}", level="error")

    @admin.action(description="Reject proposal")
    def reject_proposal(self, request, queryset):
        count = queryset.filter(status=BootstrapProposal.Status.PROPOSED).update(
            status=BootstrapProposal.Status.FAILED,
            error_message="Rejected by admin",
        )
        self.message_user(request, f"{count} proposal(s) rejected.")

    def _apply_proposal(self, proposal):
        """Create departments, agents, and documents from the proposal JSON."""
        project = proposal.project
        data = proposal.proposal
        if not data or "departments" not in data:
            raise ValueError("Invalid proposal — missing departments")

        for dept_data in data["departments"]:
            department, _ = Department.objects.get_or_create(
                project=project,
                name=dept_data["name"],
            )

            # Create documents
            for doc_data in dept_data.get("documents", []):
                doc = Document.objects.create(
                    title=doc_data["title"],
                    content=doc_data.get("content", ""),
                    department=department,
                )
                for tag_name in doc_data.get("tags", []):
                    tag, _ = Tag.objects.get_or_create(name=tag_name.lower())
                    doc.tags.add(tag)

            # Create agents
            created_agents = {}
            for agent_data in dept_data.get("agents", []):
                agent = Agent.objects.create(
                    name=agent_data["name"],
                    agent_type=agent_data["agent_type"],
                    department=department,
                    instructions=agent_data.get("instructions", ""),
                    auto_exec_hourly=agent_data.get("auto_exec_hourly", False),
                )
                created_agents[agent_data["agent_type"]] = agent

            # Wire superior relationships: campaign is superior to twitter/reddit
            campaign = created_agents.get("campaign")
            if campaign:
                for agent_type in ("twitter", "reddit"):
                    sub = created_agents.get(agent_type)
                    if sub:
                        sub.superior = campaign
                        sub.save(update_fields=["superior"])
```

- [ ] **Step 3: Update projects/admin/project_admin.py**

Replace the entire file:

```python
from django.contrib import admin
from django.contrib import messages

from projects.models import Project, Department, Source, BootstrapProposal


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1
    fields = ("name",)
    show_change_link = True


class SourceInline(admin.TabularInline):
    model = Source
    extra = 0
    fields = ("source_type", "original_filename", "url", "raw_content", "word_count", "created_at")
    readonly_fields = ("word_count", "created_at")
    show_change_link = True


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "source_count", "created_at")
    search_fields = ("name", "owner__email")
    ordering = ("-updated_at",)
    inlines = [SourceInline, DepartmentInline]
    actions = ["bootstrap_project"]

    @admin.display(description="Sources")
    def source_count(self, obj):
        return obj.sources.count()

    @admin.action(description="Bootstrap Project — analyze sources and propose setup")
    def bootstrap_project(self, request, queryset):
        from projects.tasks import bootstrap_project as bootstrap_task

        for project in queryset:
            if not project.goal:
                self.message_user(request, f"{project.name}: needs a goal before bootstrapping.", level=messages.WARNING)
                continue

            source_count = project.sources.count()
            if source_count == 0:
                self.message_user(request, f"{project.name}: needs at least one source.", level=messages.WARNING)
                continue

            proposal = BootstrapProposal.objects.create(
                project=project,
                status=BootstrapProposal.Status.PENDING,
            )
            bootstrap_task.delay(str(proposal.id))
            self.message_user(
                request,
                f"Bootstrap started for {project.name}. Check Bootstrap Proposals for results.",
                level=messages.SUCCESS,
            )
```

- [ ] **Step 4: Update projects/admin/__init__.py**

Replace the entire file:

```python
from .project_admin import ProjectAdmin
from .department_admin import DepartmentAdmin
from .document_admin import DocumentAdmin
from .source_admin import SourceAdmin
from .bootstrap_proposal_admin import BootstrapProposalAdmin

__all__ = ["ProjectAdmin", "DepartmentAdmin", "DocumentAdmin", "SourceAdmin", "BootstrapProposalAdmin"]
```

- [ ] **Step 5: Commit**

```bash
git add backend/projects/admin/
git commit -m "feat: admin for Source, BootstrapProposal, and Project bootstrap action"
```

---

### Task 8: Source Extraction on Save & Smoke Test

**Files:**
- Modify: `backend/projects/admin/source_admin.py` (add save_model hook)

- [ ] **Step 1: Add save_model to SourceAdmin for auto-extraction**

Add this method to the `SourceAdmin` class in `backend/projects/admin/source_admin.py`:

```python
    def save_model(self, request, obj, form, change):
        """Auto-extract text and compute metadata when a source is saved."""
        # Set user if not set
        if not obj.user_id:
            obj.user = request.user

        # Handle file upload from admin
        uploaded_file = request.FILES.get("file_upload")
        if uploaded_file and obj.source_type == "file":
            content = uploaded_file.read()
            obj.original_filename = uploaded_file.name
            obj.file_size = len(content)
            obj.content_type = uploaded_file.content_type or ""
            obj.file_format = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
            obj.content_hash = compute_content_hash(content)
            obj.file_key = upload_file(content, uploaded_file.name, str(obj.project_id))

        super().save_model(request, obj, form, change)

        # Extract text after save
        if not obj.extracted_text:
            from projects.extraction import extract_text
            text = extract_text(obj)
            if text:
                obj.extracted_text = text
                obj.word_count = len(text.split())
                obj.save(update_fields=["extracted_text", "word_count"])
```

- [ ] **Step 2: Verify the full flow**

Run:
```bash
cd backend && source venv/bin/activate && python manage.py makemigrations projects && python manage.py migrate
```

Start the server:
```bash
python manage.py runserver 8000
```

In a second terminal, start Celery:
```bash
cd backend && source venv/bin/activate && celery -A config worker --loglevel=info
```

Open http://localhost:8000/admin/:

1. Open an existing Project (or create one with a goal)
2. In the Source inline, add a text source: source_type=text, raw_content="We are a boutique hotel in Berlin, 45 rooms, targeting business travelers. Professional but friendly tone."
3. Save the project
4. Select the project in the list view, run "Bootstrap Project" action
5. Navigate to Bootstrap Proposals — verify a proposal with status=pending/processing/proposed appears
6. Once status=proposed, check the proposal JSON
7. Run "Approve & Apply" — verify departments, agents, and documents are created

- [ ] **Step 3: Commit**

```bash
git add backend/projects/
git commit -m "feat: auto-extraction on source save + complete bootstrap flow"
```
