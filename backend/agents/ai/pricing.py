"""
Claude model pricing. Single source of truth for cost estimation.
Update when Anthropic changes pricing.
"""

# Per-million-token pricing (USD)
MODEL_PRICING = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD based on model and token counts."""
    prices = MODEL_PRICING.get(model, MODEL_PRICING["claude-opus-4-6"])
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
