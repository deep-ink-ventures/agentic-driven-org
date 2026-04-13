"""Tests for the pricing utility."""

import pytest

from agents.ai.pricing import MODEL_PRICING, estimate_cost


class TestEstimateCost:
    def test_sonnet_pricing(self):
        # 1M input tokens at $3/M + 1M output tokens at $15/M = $18
        cost = estimate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000)
        assert cost == pytest.approx(18.0)

    def test_opus_pricing(self):
        # 1M input at $15/M + 1M output at $75/M = $90
        cost = estimate_cost("claude-opus-4-6", 1_000_000, 1_000_000)
        assert cost == pytest.approx(90.0)

    def test_haiku_pricing(self):
        # 1M input at $0.80/M + 1M output at $4/M = $4.80
        cost = estimate_cost("claude-haiku-4-5", 1_000_000, 1_000_000)
        assert cost == pytest.approx(4.80)

    def test_zero_tokens(self):
        cost = estimate_cost("claude-sonnet-4-6", 0, 0)
        assert cost == 0.0

    def test_small_token_count(self):
        # 1000 input tokens with Sonnet: 1000 * 3.0 / 1M = 0.003
        cost = estimate_cost("claude-sonnet-4-6", 1000, 0)
        assert cost == pytest.approx(0.003)

    def test_unknown_model_uses_opus_default(self):
        cost_unknown = estimate_cost("nonexistent-model", 1_000_000, 1_000_000)
        cost_opus = estimate_cost("claude-opus-4-6", 1_000_000, 1_000_000)
        assert cost_unknown == cost_opus

    def test_model_pricing_dict_has_expected_keys(self):
        for _model, prices in MODEL_PRICING.items():
            assert "input" in prices
            assert "output" in prices
            assert prices["input"] > 0
            assert prices["output"] > 0

    def test_output_only(self):
        # 500 output tokens with Haiku: 500 * 4.0 / 1M = 0.002
        cost = estimate_cost("claude-haiku-4-5", 0, 500)
        assert cost == pytest.approx(0.002)
