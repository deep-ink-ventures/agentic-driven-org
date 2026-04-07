from unittest.mock import MagicMock, patch


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

        result, usage = call_claude(
            system_prompt="You are helpful",
            user_message="Hi",
        )

        assert result == "Hello from Claude"
        assert usage["model"] == "claude-opus-4-6"
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        mock_client.messages.create.assert_called_once_with(
            model="claude-opus-4-6",
            max_tokens=8192,
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

        result, usage = call_claude(
            system_prompt="sys",
            user_message="msg",
        )

        assert result == "First part. Second part."
        assert usage["input_tokens"] == 200
        assert usage["output_tokens"] == 100

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


class TestCallClaudeWithTools:
    @patch("agents.ai.claude_client._client", None)
    @patch("agents.ai.claude_client.anthropic")
    def test_returns_text_and_tool_input(self, mock_anthropic):
        from agents.ai.claude_client import call_claude_with_tools

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Here is my analysis."

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.input = {"verdict": "approved", "score": 9}

        mock_message = MagicMock()
        mock_message.content = [text_block, tool_block]
        mock_message.usage.input_tokens = 150
        mock_message.usage.output_tokens = 75

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        tools = [{"name": "submit_verdict", "input_schema": {}}]
        text, tool_input, usage = call_claude_with_tools(
            system_prompt="You are a reviewer",
            user_message="Review this",
            tools=tools,
        )

        assert text == "Here is my analysis."
        assert tool_input == {"verdict": "approved", "score": 9}
        assert usage["model"] == "claude-opus-4-6"
        assert usage["input_tokens"] == 150
        assert usage["output_tokens"] == 75
        call_kwargs = mock_client.messages.create.call_args
        assert "tools" in call_kwargs.kwargs
        assert call_kwargs.kwargs["tools"] == tools

    @patch("agents.ai.claude_client._client", None)
    @patch("agents.ai.claude_client.anthropic")
    def test_returns_none_when_no_tool_call(self, mock_anthropic):
        from agents.ai.claude_client import call_claude_with_tools

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Just text, no tool."

        mock_message = MagicMock()
        mock_message.content = [text_block]
        mock_message.usage.input_tokens = 50
        mock_message.usage.output_tokens = 20

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        text, tool_input, usage = call_claude_with_tools(
            system_prompt="sys",
            user_message="msg",
            tools=[],
        )

        assert text == "Just text, no tool."
        assert tool_input is None

    @patch("agents.ai.claude_client._client", None)
    @patch("agents.ai.claude_client.anthropic")
    def test_extracts_first_tool_use_only(self, mock_anthropic):
        from agents.ai.claude_client import call_claude_with_tools

        tool_block1 = MagicMock()
        tool_block1.type = "tool_use"
        tool_block1.input = {"first": True}

        tool_block2 = MagicMock()
        tool_block2.type = "tool_use"
        tool_block2.input = {"second": True}

        mock_message = MagicMock()
        mock_message.content = [tool_block1, tool_block2]
        mock_message.usage.input_tokens = 80
        mock_message.usage.output_tokens = 40

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        text, tool_input, usage = call_claude_with_tools(
            system_prompt="sys",
            user_message="msg",
            tools=[],
        )

        assert tool_input == {"first": True}


class TestParseJsonResponse:
    def test_plain_json(self):
        from agents.ai.claude_client import parse_json_response

        result = parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_fenced_json(self):
        from agents.ai.claude_client import parse_json_response

        result = parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_fenced_json_no_lang(self):
        from agents.ai.claude_client import parse_json_response

        result = parse_json_response('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        from agents.ai.claude_client import parse_json_response

        result = parse_json_response('Here is the JSON:\n{"key": "value"}\nDone.')
        assert result == {"key": "value"}

    def test_unescaped_newlines_in_string_values(self):
        from agents.ai.claude_client import parse_json_response

        # Simulate Claude putting literal newlines inside a JSON string value
        raw = '```json\n{"enriched_goal": "Line 1\nLine 2\nLine 3", "summary": "ok"}\n```'
        result = parse_json_response(raw)
        assert result is not None
        assert result["enriched_goal"] == "Line 1\nLine 2\nLine 3"
        assert result["summary"] == "ok"

    def test_unescaped_newlines_with_nested_objects(self):
        from agents.ai.claude_client import parse_json_response

        raw = '{"goal": "Has\nnewlines\nin it", "departments": [{"type": "writers_room"}]}'
        result = parse_json_response(raw)
        assert result is not None
        assert "newlines" in result["goal"]
        assert result["departments"][0]["type"] == "writers_room"

    def test_returns_none_for_garbage(self):
        from agents.ai.claude_client import parse_json_response

        assert parse_json_response("not json at all") is None
        assert parse_json_response("") is None
