"""Tests for projects.storage module — LOCAL backend only."""

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from projects.storage import (
    _guess_content_type,
    _local_delete,
    _local_delete_project,
    _local_get_url,
    _local_upload,
    upload_file,
)


@pytest.fixture
def media_root(tmp_path):
    return tmp_path / "media"


@pytest.fixture
def project_id():
    return str(uuid.uuid4())


# ── _local_upload ──────────────────────────────────────────────────────────────


class TestLocalUpload:
    def test_creates_file(self, media_root, project_id):
        with patch("projects.storage.LOCAL_MEDIA_ROOT", media_root):
            rel_path = _local_upload(b"hello", "test.txt", project_id, "sources")

        assert rel_path.startswith(f"projects/{project_id}/sources/")
        assert rel_path.endswith("_test.txt")
        full_path = media_root / rel_path
        assert full_path.exists()
        assert full_path.read_bytes() == b"hello"

    def test_creates_parent_dirs(self, media_root, project_id):
        with patch("projects.storage.LOCAL_MEDIA_ROOT", media_root):
            rel_path = _local_upload(b"data", "file.pdf", project_id, "docs")

        full_path = media_root / rel_path
        assert full_path.parent.is_dir()

    def test_unique_file_ids(self, media_root, project_id):
        with patch("projects.storage.LOCAL_MEDIA_ROOT", media_root):
            p1 = _local_upload(b"a", "f.txt", project_id, "sources")
            p2 = _local_upload(b"b", "f.txt", project_id, "sources")
        assert p1 != p2


# ── _local_get_url ─────────────────────────────────────────────────────────────


class TestLocalGetUrl:
    def test_returns_media_url(self):
        url = _local_get_url("projects/abc/sources/file.txt")
        assert url == "/media/projects/abc/sources/file.txt"

    def test_empty_path(self):
        assert _local_get_url("") == ""


# ── _local_delete ──────────────────────────────────────────────────────────────


class TestLocalDelete:
    def test_deletes_file(self, media_root):
        # Create file first
        rel_path = "projects/abc/sources/test.txt"
        full_path = media_root / rel_path
        full_path.parent.mkdir(parents=True)
        full_path.write_bytes(b"data")

        with patch("projects.storage.LOCAL_MEDIA_ROOT", media_root):
            result = _local_delete(rel_path)

        assert result is True
        assert not full_path.exists()

    def test_missing_file(self, media_root):
        with patch("projects.storage.LOCAL_MEDIA_ROOT", media_root):
            result = _local_delete("projects/abc/nonexistent.txt")
        assert result is False

    def test_empty_path(self):
        assert _local_delete("") is False


# ── _local_delete_project ─────────────────────────────────────────────────────


class TestLocalDeleteProject:
    def test_removes_directory(self, media_root):
        pid = "test-proj-id"
        proj_dir = media_root / "projects" / pid
        (proj_dir / "sources").mkdir(parents=True)
        (proj_dir / "sources" / "a.txt").write_bytes(b"a")
        (proj_dir / "sources" / "b.txt").write_bytes(b"b")

        with patch("projects.storage.LOCAL_MEDIA_ROOT", media_root):
            count = _local_delete_project(pid)

        assert count == 2
        assert not proj_dir.exists()

    def test_nonexistent_project(self, media_root):
        with patch("projects.storage.LOCAL_MEDIA_ROOT", media_root):
            count = _local_delete_project("nonexistent")
        assert count == 0


# ── upload_file dispatch ──────────────────────────────────────────────────────


class TestUploadFile:
    @patch("projects.storage.STORAGE_BACKEND", "local")
    def test_dispatches_to_local(self, media_root, project_id):
        with patch("projects.storage._local_upload", wraps=_local_upload) as mock_upload:
            with patch("projects.storage.LOCAL_MEDIA_ROOT", media_root):
                result = upload_file(b"data", "test.txt", project_id)
        mock_upload.assert_called_once()
        assert "test.txt" in result


# ── _guess_content_type ───────────────────────────────────────────────────────


class TestGuessContentType:
    def test_pdf(self):
        assert _guess_content_type("report.pdf") == "application/pdf"

    def test_docx(self):
        ct = _guess_content_type("doc.docx")
        assert ct == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def test_txt(self):
        assert _guess_content_type("notes.txt") == "text/plain"

    def test_md(self):
        assert _guess_content_type("README.md") == "text/plain"

    def test_unknown(self):
        assert _guess_content_type("image.png") == "application/octet-stream"

    def test_no_extension(self):
        assert _guess_content_type("Makefile") == "application/octet-stream"
