"""
Claude API client for agent reasoning.

All agent blueprint code calls this module to interact with Claude.
"""

import json
import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to backend/.env")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def reset_client():
    """Reset the cached client (e.g. after config change). Mostly for testing."""
    global _client
    _client = None


def call_claude(
    system_prompt: str,
    user_message: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 8192,
) -> tuple[str, dict]:
    """
    Call Claude API and return (response_text, usage_dict).
    usage_dict: {model, input_tokens, output_tokens}
    """
    client = _get_client()

    logger.info("Calling Claude: model=%s, system_len=%d, msg_len=%d", model, len(system_prompt), len(user_message))

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = ""
    for block in message.content:
        if block.type == "text":
            response_text += block.text

    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    from agents.ai.pricing import estimate_cost

    cost = estimate_cost(model, input_tokens, output_tokens)

    usage = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }

    logger.info("Claude response: model=%s input=%d output=%d cost=$%.4f", model, input_tokens, output_tokens, cost)

    return response_text, usage


def call_claude_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    model: str = "claude-opus-4-6",
    max_tokens: int = 8192,
    force_tool: str | None = None,
) -> tuple[str, dict | None, dict]:
    """
    Call Claude API with tools and return (response_text, tool_input_or_None, usage_dict).
    Concatenates text blocks into the report. Extracts the first tool_use block's
    input as structured data. Returns None for tool_input if no tool was called.

    If force_tool is set, the API will require the model to call that tool,
    guaranteeing schema-validated structured output.
    """
    client = _get_client()
    logger.info(
        "Calling Claude with tools: model=%s, system_len=%d, msg_len=%d, tools=%d, force=%s",
        model,
        len(system_prompt),
        len(user_message),
        len(tools),
        force_tool,
    )
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
        "tools": tools,
    }
    if force_tool:
        kwargs["tool_choice"] = {"type": "tool", "name": force_tool}
    message = client.messages.create(**kwargs)
    response_text = ""
    tool_input = None
    for block in message.content:
        if block.type == "text":
            response_text += block.text
        elif block.type == "tool_use" and tool_input is None:
            tool_input = block.input

    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    from agents.ai.pricing import estimate_cost

    cost = estimate_cost(model, input_tokens, output_tokens)

    usage = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }
    logger.info(
        "Claude response (tools): model=%s input=%d output=%d cost=$%.4f tool_called=%s",
        model,
        input_tokens,
        output_tokens,
        cost,
        tool_input is not None,
    )
    return response_text, tool_input, usage


def call_claude_tool_loop(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    handle_tool_call: callable,
    model: str = "claude-opus-4-6",
    max_tokens: int = 8192,
    max_turns: int = 50,
) -> tuple[str, dict]:
    """Multi-turn tool loop: Claude calls tools, we handle them, feed results back.

    Args:
        handle_tool_call: callable(name, input) -> str (JSON result).
            Called for each tool_use block. Return value is sent back as tool_result.
        max_turns: safety cap on conversation turns.

    Returns (final_response_text, cumulative_usage_dict).
    """
    client = _get_client()
    from agents.ai.pricing import estimate_cost

    messages = [{"role": "user", "content": user_message}]
    total_input = 0
    total_output = 0
    total_cost = 0.0
    final_text = ""

    for _turn in range(max_turns):
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )

        total_input += message.usage.input_tokens
        total_output += message.usage.output_tokens
        total_cost += estimate_cost(model, message.usage.input_tokens, message.usage.output_tokens)

        # Collect text and tool calls
        text_parts = []
        tool_uses = []
        for block in message.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        final_text = "".join(text_parts)

        if message.stop_reason == "end_turn" or not tool_uses:
            break

        # Process tool calls and build tool results
        assistant_content = message.content  # preserve full content for conversation
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for tool_use in tool_uses:
            result_str = handle_tool_call(tool_use.name, tool_use.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_str,
                }
            )

        messages.append({"role": "user", "content": tool_results})

    usage = {
        "model": model,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cost_usd": total_cost,
    }
    logger.info(
        "Claude tool loop: model=%s turns=%d input=%d output=%d cost=$%.4f",
        model,
        _turn + 1,
        total_input,
        total_output,
        total_cost,
    )
    return final_text, usage


def stream_claude(
    system_prompt: str,
    user_message: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 8192,
    on_progress: callable = None,
) -> tuple[str, dict]:
    """
    Stream Claude API response, calling on_progress(accumulated_text, tokens_so_far) periodically.
    Returns (response_text, usage_dict) same as call_claude.
    """
    client = _get_client()

    logger.info("Streaming Claude: model=%s, system_len=%d, msg_len=%d", model, len(system_prompt), len(user_message))

    accumulated = ""
    input_tokens = 0
    output_tokens = 0

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            accumulated += text
            output_tokens += 1  # approximate token count
            if on_progress and output_tokens % 10 == 0:
                on_progress(accumulated, output_tokens)

        # Get final message for accurate usage
        final = stream.get_final_message()
        input_tokens = final.usage.input_tokens
        output_tokens = final.usage.output_tokens

    # Final progress callback
    if on_progress:
        on_progress(accumulated, output_tokens)

    from agents.ai.pricing import estimate_cost

    cost = estimate_cost(model, input_tokens, output_tokens)

    usage = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }

    logger.info(
        "Claude stream complete: model=%s input=%d output=%d cost=$%.4f", model, input_tokens, output_tokens, cost
    )

    return accumulated, usage


def parse_json_response(response: str) -> dict | None:
    """
    Parse a JSON response from Claude, stripping markdown fences if present.
    Returns the parsed dict or None if parsing fails.
    """
    import re

    cleaned = response.strip()
    # Strip markdown fences (```json ... ``` or ``` ... ```)
    fence_match = re.match(r"^```(?:json)?\s*\n(.*?)```\s*$", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback: find the first { and try progressively larger substrings ending with }
    first_brace = cleaned.find("{")
    if first_brace == -1:
        return None
    # Try from the last } backwards
    last_brace = cleaned.rfind("}")
    if last_brace <= first_brace:
        return None
    candidate = cleaned[first_brace : last_brace + 1]
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        pass
    # Last resort: fix common Claude JSON issues (unescaped control chars in strings)
    # Replace literal newlines/tabs inside JSON string values with their escaped forms
    try:
        fixed = _fix_json_control_chars(candidate)
        return json.loads(fixed)
    except (json.JSONDecodeError, ValueError):
        return None


def _fix_json_control_chars(s: str) -> str:
    """Fix unescaped control characters inside JSON string values.

    Claude sometimes produces JSON with literal newlines inside string values
    (especially in enriched_goal fields containing markdown). This fixes them
    by replacing literal control chars with their JSON escape sequences,
    but only inside quoted strings.
    """

    result = []
    in_string = False
    escape_next = False
    for char in s:
        if escape_next:
            result.append(char)
            escape_next = False
            continue
        if char == "\\" and in_string:
            result.append(char)
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            result.append(char)
            continue
        if in_string:
            if char == "\n":
                result.append("\\n")
                continue
            if char == "\r":
                result.append("\\r")
                continue
            if char == "\t":
                result.append("\\t")
                continue
        result.append(char)
    return "".join(result)
