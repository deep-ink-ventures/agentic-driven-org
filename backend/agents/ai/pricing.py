"""
Claude model pricing. Single source of truth for cost estimation.
Update when Anthropic changes pricing.

Prompt caching pricing:
- Cache write: 1.25x input price (one-time cost when content is first cached)
- Cache read:  0.1x input price (90% discount on subsequent hits within 5-min TTL)
- Non-cached input: standard input price
"""

# Per-million-token pricing (USD)
MODEL_PRICING = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
}


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
) -> float:
    """Estimate cost in USD based on model and token counts.

    With prompt caching, the API reports three input categories:
    - input_tokens: non-cached input (standard price)
    - cache_creation_input_tokens: first-time cache write (1.25x price)
    - cache_read_input_tokens: cache hits (0.1x price)
    """
    prices = MODEL_PRICING.get(model, MODEL_PRICING["claude-opus-4-6"])
    input_cost = input_tokens * prices["input"]
    output_cost = output_tokens * prices["output"]
    cache_write_cost = cache_creation_input_tokens * prices["input"] * 1.25
    cache_read_cost = cache_read_input_tokens * prices["input"] * 0.1
    return (input_cost + output_cost + cache_write_cost + cache_read_cost) / 1_000_000
