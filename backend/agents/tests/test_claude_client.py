from unittest.mock import patch, MagicMock

import pytest


class TestCallClaude:
    @patch("agents.ai.claude_client._client", None)
    @patch("agents.ai.claude_client.anthropic")
    def test_call_claude_returns_text(self, mock_anthropic):
        from agents.ai.claude_client import call_claude

        # Set up mock response
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Hello from Claude"

        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.usage.input_tokens = 100
        mock_message.usage.output_tokens = 50

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        result = call_claude(
            system_prompt="You are helpful",
            user_message="Hi",
        )

        assert result == "Hello from Claude"
        mock_client.messages.create.assert_called_once_with(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="You are helpful",
            messages=[{"role": "user", "content": "Hi"}],
        )

    @patch("agents.ai.claude_client._client", None)
    @patch("agents.ai.claude_client.anthropic")
    def test_multiple_content_blocks(self, mock_anthropic):
        from agents.ai.claude_client import call_claude

        block1 = MagicMock()
        block1.type = "text"
        block1.text = "First part. "

        block2 = MagicMock()
        block2.type = "tool_use"  # non-text block
        block2.text = "ignored"

        block3 = MagicMock()
        block3.type = "text"
        block3.text = "Second part."

        mock_message = MagicMock()
        mock_message.content = [block1, block2, block3]
        mock_message.usage.input_tokens = 200
        mock_message.usage.output_tokens = 100

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        result = call_claude(
            system_prompt="sys",
            user_message="msg",
        )

        assert result == "First part. Second part."

    @patch("agents.ai.claude_client._client", None)
    @patch("agents.ai.claude_client.anthropic")
    def test_singleton_client_pattern(self, mock_anthropic):
        """After first call, _get_client reuses the same instance."""
        import agents.ai.claude_client as mod

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = []
        mock_message.usage.input_tokens = 0
        mock_message.usage.output_tokens = 0
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        # First call creates client
        mod._client = None
        mod._get_client()
        assert mock_anthropic.Anthropic.call_count == 1

        # Second call reuses
        mod._get_client()
        assert mock_anthropic.Anthropic.call_count == 1

        # Reset for other tests
        mod._client = None
