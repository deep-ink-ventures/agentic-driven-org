"""
Claude API client for agent reasoning.

All agent blueprint code calls this module to interact with Claude.
"""

import json
import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)


class APILimitReached(Exception):
    """Raised when the Anthropic API usage limit is hit. Not a transient error — requires limit change."""

    pass


def _check_api_limit(exc: Exception):
    """If the exception is a hard API usage/billing limit, raise APILimitReached instead."""
    msg = str(exc)
    if ("usage limits" in msg and "regain access" in msg) or "credit balance is too low" in msg:
        raise APILimitReached(msg) from exc


_client = None

_CACHE_CONTROL = {"type": "ephemeral"}


def _make_system_blocks(system_prompt: str) -> list[dict]:
    """Convert system prompt string to content blocks with cache_control."""
    return [{"type": "text", "text": system_prompt, "cache_control": _CACHE_CONTROL}]


def _make_user_content(user_message: str, cache_context: str | None = None) -> str | list[dict]:
    """Build user message content, optionally splitting a cacheable prefix.

    If cache_context is provided, the user message is split into two content blocks:
    1. The shared context (project goal, department docs, etc.) — cached
    2. The rest of the message (task-specific) — not cached

    This means that when multiple agents in the same department/sprint run,
    the shared context prefix is read from cache at 0.1x the input price.
    """
    if not cache_context:
        return user_message
    return [
        {"type": "text", "text": cache_context, "cache_control": _CACHE_CONTROL},
        {"type": "text", "text": user_message},
    ]


def _extract_usage(message, model: str) -> dict:
    """Extract usage dict from API response, including cache token breakdowns."""
    from agents.ai.pricing import estimate_cost

    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    cache_creation = getattr(message.usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(message.usage, "cache_read_input_tokens", 0) or 0

    cost = estimate_cost(
        model,
        input_tokens,
        output_tokens,
        cache_creation_input_tokens=cache_creation,
        cache_read_input_tokens=cache_read,
    )

    usage = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }
    if cache_creation or cache_read:
        usage["cache_creation_input_tokens"] = cache_creation
        usage["cache_read_input_tokens"] = cache_read

    return usage


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
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8192,
    cache_context: str | None = None,
) -> tuple[str, dict]:
    """
    Call Claude API and return (response_text, usage_dict).
    usage_dict: {model, input_tokens, output_tokens, cost_usd, cache_*}

    Args:
        cache_context: Optional shared context prefix to cache separately.
                      When provided, the system prompt is also cached.
    """
    client = _get_client()

    logger.info("Calling Claude: model=%s, system_len=%d, msg_len=%d", model, len(system_prompt), len(user_message))

    system = _make_system_blocks(system_prompt) if cache_context else system_prompt
    content = _make_user_content(user_message, cache_context)

    try:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
        )
    except (anthropic.BadRequestError, anthropic.APIError) as exc:
        _check_api_limit(exc)
        raise

    response_text = ""
    for block in message.content:
        if block.type == "text":
            response_text += block.text

    usage = _extract_usage(message, model)

    logger.info(
        "Claude response: model=%s input=%d output=%d cost=$%.4f cache_read=%d",
        model,
        usage["input_tokens"],
        usage["output_tokens"],
        usage["cost_usd"],
        usage.get("cache_read_input_tokens", 0),
    )

    return response_text, usage


def call_claude_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8192,
    force_tool: str | None = None,
    cache_context: str | None = None,
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

    system = _make_system_blocks(system_prompt) if cache_context else system_prompt
    content = _make_user_content(user_message, cache_context)

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": content}],
        "tools": tools,
    }
    if force_tool:
        kwargs["tool_choice"] = {"type": "tool", "name": force_tool}
    try:
        message = client.messages.create(**kwargs)
    except (anthropic.BadRequestError, anthropic.APIError) as exc:
        _check_api_limit(exc)
        raise
    response_text = ""
    tool_input = None
    for block in message.content:
        if block.type == "text":
            response_text += block.text
        elif block.type == "tool_use" and tool_input is None:
            tool_input = block.input

    usage = _extract_usage(message, model)
    logger.info(
        "Claude response (tools): model=%s input=%d output=%d cost=$%.4f tool_called=%s cache_read=%d",
        model,
        usage["input_tokens"],
        usage["output_tokens"],
        usage["cost_usd"],
        tool_input is not None,
        usage.get("cache_read_input_tokens", 0),
    )
    return response_text, tool_input, usage


def call_claude_tool_loop(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    handle_tool_call: callable,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8192,
    max_turns: int = 50,
    cache_context: str | None = None,
) -> tuple[str, dict]:
    """Multi-turn tool loop: Claude calls tools, we handle them, feed results back.

    Args:
        handle_tool_call: callable(name, input) -> str (JSON result).
            Called for each tool_use block. Return value is sent back as tool_result.
        max_turns: safety cap on conversation turns.
        cache_context: Optional shared context prefix to cache. The system prompt
                      is always cached in tool loops since it's resent every turn.

    Returns (final_response_text, cumulative_usage_dict).
    """
    client = _get_client()

    # Tool loops always benefit from caching the system prompt — it's resent every turn.
    system = _make_system_blocks(system_prompt)
    first_content = _make_user_content(user_message, cache_context)

    messages = [{"role": "user", "content": first_content}]
    total_input = 0
    total_output = 0
    total_cost = 0.0
    total_cache_creation = 0
    total_cache_read = 0
    final_text = ""

    for _turn in range(max_turns):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=tools,
            )
        except (anthropic.BadRequestError, anthropic.APIError) as exc:
            _check_api_limit(exc)
            raise

        turn_usage = _extract_usage(message, model)
        total_input += turn_usage["input_tokens"]
        total_output += turn_usage["output_tokens"]
        total_cost += turn_usage["cost_usd"]
        total_cache_creation += turn_usage.get("cache_creation_input_tokens", 0)
        total_cache_read += turn_usage.get("cache_read_input_tokens", 0)

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
    if total_cache_creation or total_cache_read:
        usage["cache_creation_input_tokens"] = total_cache_creation
        usage["cache_read_input_tokens"] = total_cache_read

    logger.info(
        "Claude tool loop: model=%s turns=%d input=%d output=%d cost=$%.4f cache_read=%d",
        model,
        _turn + 1,
        total_input,
        total_output,
        total_cost,
        total_cache_read,
    )
    return final_text, usage


def stream_claude(
    system_prompt: str,
    user_message: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8192,
    on_progress: callable = None,
    cache_context: str | None = None,
) -> tuple[str, dict]:
    """
    Stream Claude API response, calling on_progress(accumulated_text, tokens_so_far) periodically.
    Returns (response_text, usage_dict) same as call_claude.
    """
    client = _get_client()

    logger.info("Streaming Claude: model=%s, system_len=%d, msg_len=%d", model, len(system_prompt), len(user_message))

    system = _make_system_blocks(system_prompt) if cache_context else system_prompt
    content = _make_user_content(user_message, cache_context)

    accumulated = ""
    output_tokens = 0

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        for text in stream.text_stream:
            accumulated += text
            output_tokens += 1  # approximate token count
            if on_progress and output_tokens % 10 == 0:
                on_progress(accumulated, output_tokens)

        # Get final message for accurate usage
        final = stream.get_final_message()

    # Final progress callback
    if on_progress:
        on_progress(accumulated, final.usage.output_tokens)

    usage = _extract_usage(final, model)

    logger.info(
        "Claude stream complete: model=%s input=%d output=%d cost=$%.4f cache_read=%d",
        model,
        usage["input_tokens"],
        usage["output_tokens"],
        usage["cost_usd"],
        usage.get("cache_read_input_tokens", 0),
    )

    return accumulated, usage


def call_claude_structured(
    system_prompt: str,
    user_message: str,
    output_schema: dict,
    tool_name: str = "structured_output",
    tool_description: str = "Submit your structured response",
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8192,
    on_progress: callable = None,
    cache_context: str | None = None,
) -> tuple[dict, dict]:
    """
    Call Claude and force structured JSON output via tool use.

    Instead of asking Claude to return JSON in a text response (which it wraps
    in markdown fences, adds literal newlines in strings, etc.), this forces
    Claude to call a tool with a strict JSON schema. The SDK validates the
    schema automatically — no parsing, no fences, no hacks.

    Args:
        output_schema: JSON Schema for the output (the tool's input_schema).
        tool_name: Name for the forced tool.
        tool_description: Description shown to Claude.
        on_progress: Optional callback(text, tokens) for streaming progress.
                     When provided, streams the response for UI feedback
                     but still extracts the tool call result.
        cache_context: Optional shared context prefix to cache separately.

    Returns:
        (structured_data, usage_dict) where structured_data is the validated dict.

    Raises:
        ValueError: If Claude doesn't produce a valid tool call.
    """
    client = _get_client()

    tool = {
        "name": tool_name,
        "description": tool_description,
        "input_schema": output_schema,
    }

    logger.info(
        "Calling Claude structured: model=%s, tool=%s, system_len=%d, msg_len=%d",
        model,
        tool_name,
        len(system_prompt),
        len(user_message),
    )

    system = _make_system_blocks(system_prompt) if cache_context else system_prompt
    user_content = _make_user_content(user_message, cache_context)

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_content}],
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": tool_name},
    }

    if on_progress:
        # Stream for progress updates, but still extract tool_use block
        tool_input = None
        accumulated_text = ""

        try:
            stream_ctx = client.messages.stream(**kwargs)
        except (anthropic.BadRequestError, anthropic.APIError) as exc:
            _check_api_limit(exc)
            raise
        with stream_ctx as stream:
            for event in stream:
                # Provide progress feedback from text deltas
                if (
                    hasattr(event, "type")
                    and event.type == "content_block_delta"
                    and hasattr(event.delta, "partial_json")
                ):
                    accumulated_text += event.delta.partial_json
                    if len(accumulated_text) % 100 < 10:
                        on_progress(accumulated_text, len(accumulated_text))

            final = stream.get_final_message()

            for block in final.content:
                if block.type == "tool_use":
                    tool_input = block.input
                    break

        if on_progress:
            on_progress(accumulated_text, final.usage.output_tokens)

        usage = _extract_usage(final, model)
    else:
        try:
            message = client.messages.create(**kwargs)
        except (anthropic.BadRequestError, anthropic.APIError) as exc:
            _check_api_limit(exc)
            raise
        tool_input = None
        for block in message.content:
            if block.type == "tool_use":
                tool_input = block.input
                break

        usage = _extract_usage(message, model)

    if tool_input is None:
        raise ValueError("Claude did not produce a tool call — structured output failed")

    logger.info(
        "Claude structured complete: model=%s input=%d output=%d cost=$%.4f cache_read=%d",
        model,
        usage["input_tokens"],
        usage["output_tokens"],
        usage["cost_usd"],
        usage.get("cache_read_input_tokens", 0),
    )

    return tool_input, usage


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
