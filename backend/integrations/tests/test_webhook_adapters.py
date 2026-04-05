"""Tests for webhook adapter registry and GitHub adapter."""

import json
from unittest.mock import MagicMock, patch

from integrations.webhooks import WEBHOOK_ADAPTERS, get_adapter
from integrations.webhooks.adapters.github import GitHubWebhookAdapter


class TestAdapterRegistry:
    def test_get_github_adapter(self):
        adapter = get_adapter("github")
        assert adapter is not None
        assert isinstance(adapter, GitHubWebhookAdapter)
        assert adapter.slug == "github"

    def test_get_unknown_adapter_returns_none(self):
        assert get_adapter("unknown_service") is None

    def test_get_adapter_empty_string(self):
        assert get_adapter("") is None

    def test_github_registered(self):
        assert "github" in WEBHOOK_ADAPTERS


class TestGitHubAdapter:
    def _make_request(self, body: bytes, event_type: str = "push", action: str = "", signature: str = ""):
        """Helper to build a mock Django request."""
        request = MagicMock()
        request.body = body
        request.headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": event_type,
        }
        request.data = json.loads(body) if body else {}
        if action:
            request.data["action"] = action
        return request

    @patch("integrations.webhooks.adapters.github.github_service")
    def test_verify_delegates_to_github_service(self, mock_svc):
        mock_svc.verify_webhook_signature.return_value = True
        adapter = GitHubWebhookAdapter()
        body = b'{"test": true}'
        request = self._make_request(body, signature="sha256=abc")
        result = adapter.verify(request, "my_secret")
        assert result is True
        mock_svc.verify_webhook_signature.assert_called_once_with(body, "sha256=abc", "my_secret")

    @patch("integrations.webhooks.adapters.github.github_service")
    def test_verify_returns_false_on_bad_signature(self, mock_svc):
        mock_svc.verify_webhook_signature.return_value = False
        adapter = GitHubWebhookAdapter()
        request = self._make_request(b"{}", signature="sha256=bad")
        assert adapter.verify(request, "secret") is False

    def test_parse_event_push(self):
        adapter = GitHubWebhookAdapter()
        request = self._make_request(b'{"ref": "refs/heads/main"}', event_type="push")
        event = adapter.parse_event(request)
        assert event["event_type"] == "push"
        assert event["data"]["ref"] == "refs/heads/main"

    def test_parse_event_with_action(self):
        adapter = GitHubWebhookAdapter()
        body = json.dumps({"action": "completed"}).encode()
        request = self._make_request(body, event_type="workflow_run", action="completed")
        event = adapter.parse_event(request)
        assert event["event_type"] == "workflow_run.completed"

    def test_parse_event_no_action(self):
        adapter = GitHubWebhookAdapter()
        request = self._make_request(b"{}", event_type="ping")
        event = adapter.parse_event(request)
        assert event["event_type"] == "ping"

    @patch("integrations.webhooks.adapters.github.github_service")
    def test_check_pending_no_token(self, mock_svc):
        adapter = GitHubWebhookAdapter()
        result = adapter.check_pending([{"repo": "org/repo", "external_id": "123"}], {})
        assert result == []

    @patch("integrations.webhooks.adapters.github.github_service")
    def test_check_pending_completed_run(self, mock_svc):
        mock_svc.get_workflow_run.return_value = {"status": "completed", "conclusion": "success"}
        mock_svc.get_workflow_logs.return_value = "Build passed"
        adapter = GitHubWebhookAdapter()
        events = [{"repo": "org/repo", "external_id": "42"}]
        result = adapter.check_pending(events, {"github_token": "tok"})
        assert len(result) == 1
        assert result[0]["result"] == "Build passed"
        assert result[0]["conclusion"] == "success"

    @patch("integrations.webhooks.adapters.github.github_service")
    def test_check_pending_still_running(self, mock_svc):
        mock_svc.get_workflow_run.return_value = {"status": "in_progress"}
        adapter = GitHubWebhookAdapter()
        events = [{"repo": "org/repo", "external_id": "42"}]
        result = adapter.check_pending(events, {"github_token": "tok"})
        assert result == []
