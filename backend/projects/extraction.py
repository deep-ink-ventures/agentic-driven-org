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
