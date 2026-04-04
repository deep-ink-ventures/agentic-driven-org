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
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
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


def parse_json_response(response: str) -> dict | None:
    """
    Parse a JSON response from Claude, stripping markdown fences if present.
    Returns the parsed dict or None if parsing fails.
    """
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None
