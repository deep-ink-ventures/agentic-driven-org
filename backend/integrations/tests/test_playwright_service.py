"""Tests for the Playwright browser automation service."""

from integrations.playwright.service import run_action


class TestRunAction:
    def test_returns_dict(self):
        """run_action returns a dict."""
        result = run_action("tweet", {"content": "Hello"}, {})
        assert isinstance(result, dict)

    def test_success_flag(self):
        """run_action returns success=True on normal execution."""
        result = run_action("tweet", {"content": "Hello"}, {})
        assert result.get("success") is True

    def test_action_type_in_result(self):
        """run_action includes action_type in the returned dict."""
        result = run_action("reply", {"content": "Nice"}, {})
        assert result.get("action_type") == "reply"

    def test_result_key_present(self):
        """run_action includes a 'result' key."""
        result = run_action("navigate", {"url": "https://example.com"}, {})
        assert "result" in result

    def test_empty_params(self):
        """run_action handles empty params dict."""
        result = run_action("search", {}, {})
        assert isinstance(result, dict)
        assert result.get("success") is True

    def test_unknown_action_type(self):
        """run_action handles unknown action types without raising."""
        result = run_action("do_something_unknown", {"key": "val"}, {})
        assert isinstance(result, dict)
        assert result.get("success") is True
