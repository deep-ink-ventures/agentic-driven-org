"""Tests for GitHub service extensions: list_workflow_runs, create_or_update_file."""

import base64
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from integrations.github_dev.service import create_or_update_file, list_workflow_runs


class TestGitHubServiceExtensions(SimpleTestCase):
    """Tests for the problem-solver GitHub service functions."""

    @patch("integrations.github_dev.service.requests.get")
    def test_list_workflow_runs_returns_recent_runs(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "workflow_runs": [
                {
                    "id": 101,
                    "status": "completed",
                    "conclusion": "success",
                    "html_url": "https://github.com/owner/repo/actions/runs/101",
                    "created_at": "2026-04-11T10:00:00Z",
                    "extra_field": "ignored",
                },
                {
                    "id": 102,
                    "status": "in_progress",
                    "conclusion": None,
                    "html_url": "https://github.com/owner/repo/actions/runs/102",
                    "created_at": "2026-04-11T11:00:00Z",
                    "extra_field": "ignored",
                },
            ]
        }
        mock_get.return_value = mock_response

        result = list_workflow_runs("tok", "owner/repo", "ci.yml", per_page=2)

        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/actions/workflows/ci.yml/runs",
            headers={
                "Authorization": "Bearer tok",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params={"per_page": 2},
            timeout=30,
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 101)
        self.assertEqual(result[0]["status"], "completed")
        self.assertEqual(result[0]["conclusion"], "success")
        self.assertEqual(result[0]["url"], "https://github.com/owner/repo/actions/runs/101")
        self.assertEqual(result[0]["created_at"], "2026-04-11T10:00:00Z")
        # Ensure extra fields are not leaked
        self.assertNotIn("extra_field", result[0])

    @patch("integrations.github_dev.service.requests.put")
    @patch("integrations.github_dev.service.requests.get")
    def test_create_or_update_file_creates_new(self, mock_get, mock_put):
        # GET returns 404 — file does not exist yet
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 404
        mock_get.return_value = mock_get_resp

        # PUT creates the file
        mock_put_resp = MagicMock()
        mock_put_resp.raise_for_status = MagicMock()
        mock_put_resp.json.return_value = {
            "content": {"sha": "abc123"},
        }
        mock_put.return_value = mock_put_resp

        result = create_or_update_file("tok", "owner/repo", "path/to/file.txt", "hello", "add file")

        # Should have tried GET first
        mock_get.assert_called_once()

        # PUT should NOT include sha (new file)
        put_call = mock_put.call_args
        put_json = put_call.kwargs.get("json") or put_call[1].get("json")
        self.assertNotIn("sha", put_json)
        self.assertEqual(put_json["message"], "add file")
        self.assertEqual(put_json["content"], base64.b64encode(b"hello").decode())

        self.assertEqual(result, {"sha": "abc123"})

    @patch("integrations.github_dev.service.requests.put")
    @patch("integrations.github_dev.service.requests.get")
    def test_create_or_update_file_updates_existing(self, mock_get, mock_put):
        # GET returns existing file with sha
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {"sha": "existing_sha_999"}
        mock_get.return_value = mock_get_resp

        # PUT updates
        mock_put_resp = MagicMock()
        mock_put_resp.raise_for_status = MagicMock()
        mock_put_resp.json.return_value = {
            "content": {"sha": "new_sha_000"},
        }
        mock_put.return_value = mock_put_resp

        result = create_or_update_file("tok", "owner/repo", "README.md", "updated", "update readme")

        # PUT should include sha for update
        put_call = mock_put.call_args
        put_json = put_call.kwargs.get("json") or put_call[1].get("json")
        self.assertEqual(put_json["sha"], "existing_sha_999")
        self.assertEqual(put_json["message"], "update readme")
        self.assertEqual(put_json["content"], base64.b64encode(b"updated").decode())

        self.assertEqual(result, {"sha": "new_sha_000"})
