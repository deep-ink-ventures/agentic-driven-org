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
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def call_claude(
    system_prompt: str,
    user_message: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
) -> str:
    """
    Call Claude API and return the text response.

    Args:
        system_prompt: The system prompt for Claude
        user_message: The user message
        model: Claude model to use
        max_tokens: Max tokens in response

    Returns:
        The text content of Claude's response
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

    logger.info(
        "Claude response: input_tokens=%d, output_tokens=%d",
        message.usage.input_tokens,
        message.usage.output_tokens,
    )

    return response_text
