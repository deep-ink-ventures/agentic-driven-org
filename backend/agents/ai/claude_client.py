"""
Claude API client for agent reasoning.

All agent blueprint code calls this module to interact with Claude.
"""

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
    cost = _estimate_cost(model, input_tokens, output_tokens)

    usage = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }

    logger.info("Claude response: model=%s input=%d output=%d cost=$%.4f", model, input_tokens, output_tokens, cost)

    return response_text, usage


# Per-million-token pricing (USD). Update when pricing changes.
_PRICING = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD based on model and token counts."""
    prices = _PRICING.get(model, _PRICING["claude-sonnet-4-6"])
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
