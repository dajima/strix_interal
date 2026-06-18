"""Unit tests for strix.report.usage."""

from __future__ import annotations

import pytest
from agents.usage import Usage

from strix.report.usage import (
    LLMUsageLedger,
    _details_to_dict,
    _float_or_zero,
    _int_or_zero,
    _is_litellm_routed,
    _litellm_model_name,
    _resolve_total_tokens,
    _round_cost,
    _usage_has_activity,
)


class TestIntOrZero:
    def test_integer(self) -> None:
        assert _int_or_zero(42) == 42

    def test_string_number(self) -> None:
        assert _int_or_zero("100") == 100

    def test_none(self) -> None:
        assert _int_or_zero(None) == 0

    def test_negative_clamps(self) -> None:
        assert _int_or_zero(-5) == 0

    def test_invalid_type(self) -> None:
        assert _int_or_zero("not a number") == 0

    def test_float_truncates(self) -> None:
        assert _int_or_zero(3.9) == 3


class TestFloatOrZero:
    def test_float(self) -> None:
        assert _float_or_zero(1.5) == 1.5

    def test_none(self) -> None:
        assert _float_or_zero(None) == 0.0

    def test_negative_clamps(self) -> None:
        assert _float_or_zero(-3.14) == 0.0

    def test_string_number(self) -> None:
        assert _float_or_zero("2.5") == 2.5

    def test_invalid_type(self) -> None:
        assert _float_or_zero("abc") == 0.0


class TestRoundCost:
    def test_normal(self) -> None:
        assert _round_cost(0.123456789012) == 0.1234567890

    def test_negative_clamps_to_zero(self) -> None:
        assert _round_cost(-1.0) == 0.0

    def test_zero(self) -> None:
        assert _round_cost(0.0) == 0.0


class TestIsLitellmRouted:
    def test_none(self) -> None:
        assert _is_litellm_routed(None) is False

    def test_empty(self) -> None:
        assert _is_litellm_routed("") is False

    def test_no_slash(self) -> None:
        assert _is_litellm_routed("gpt-4o") is False

    def test_openai_prefix(self) -> None:
        assert _is_litellm_routed("openai/gpt-4o") is False

    def test_anthropic_prefix(self) -> None:
        assert _is_litellm_routed("anthropic/claude-sonnet-4") is True

    def test_deepseek(self) -> None:
        assert _is_litellm_routed("deepseek/deepseek-chat") is True


class TestLitellmModelName:
    def test_none(self) -> None:
        assert _litellm_model_name(None) is None

    def test_empty(self) -> None:
        assert _litellm_model_name("") is None

    def test_strip_litellm_prefix(self) -> None:
        assert _litellm_model_name("litellm/gpt-4o") == "gpt-4o"

    def test_strip_any_llm_prefix(self) -> None:
        assert _litellm_model_name("any-llm/claude-sonnet-4") == "claude-sonnet-4"

    def test_strip_openai_prefix(self) -> None:
        assert _litellm_model_name("openai/gpt-4o") == "gpt-4o"

    def test_no_prefix(self) -> None:
        assert _litellm_model_name("gpt-4o") == "gpt-4o"

    def test_whitespace_handled(self) -> None:
        assert _litellm_model_name("  litellm/model  ") == "model"


class TestUsageHasActivity:
    def test_empty_usage(self) -> None:
        assert _usage_has_activity(Usage()) is False

    def test_usage_with_requests(self) -> None:
        u = Usage()
        u.requests = 1
        assert _usage_has_activity(u) is True

    def test_usage_with_input_tokens(self) -> None:
        u = Usage()
        u.input_tokens = 100
        assert _usage_has_activity(u) is True


class TestResolveTotalTokens:
    def test_uses_total_tokens(self) -> None:
        u = Usage()
        u.total_tokens = 500
        assert _resolve_total_tokens(u) == 500

    def test_fallback_to_sum(self) -> None:
        u = Usage()
        u.total_tokens = 0
        u.input_tokens = 200
        u.output_tokens = 100
        assert _resolve_total_tokens(u) == 300

    def test_empty_usage(self) -> None:
        assert _resolve_total_tokens(Usage()) == 0


class TestDetailsToDict:
    def test_none(self) -> None:
        assert _details_to_dict(None) == {}

    def test_dict_input(self) -> None:
        result = _details_to_dict({"cached_tokens": 50, "empty": None})
        assert result == {"cached_tokens": 50}

    def test_list_input(self) -> None:
        result = _details_to_dict([{"cached_tokens": 30}])
        assert result == {"cached_tokens": 30}

    def test_empty_list(self) -> None:
        assert _details_to_dict([]) == {}

    def test_non_dict_non_list(self) -> None:
        assert _details_to_dict(42) == {}


class TestLLMUsageLedger:
    def test_record_none_usage(self) -> None:
        ledger = LLMUsageLedger()
        assert ledger.record(agent_id="a1", usage=None) is False

    def test_record_empty_usage(self) -> None:
        ledger = LLMUsageLedger()
        assert ledger.record(agent_id="a1", usage=Usage()) is False

    def test_record_active_usage(self) -> None:
        ledger = LLMUsageLedger()
        u = Usage()
        u.requests = 1
        u.input_tokens = 100
        u.output_tokens = 50
        u.total_tokens = 150
        assert (
            ledger.record(agent_id="agent-1", usage=u, agent_name="Scanner", model="gpt-4o") is True
        )

    def test_to_record_structure(self) -> None:
        ledger = LLMUsageLedger()
        u = Usage()
        u.requests = 2
        u.input_tokens = 200
        u.output_tokens = 100
        u.total_tokens = 300
        ledger.record(agent_id="agent-1", usage=u, agent_name="Scanner", model="gpt-4o")

        record = ledger.to_record()
        assert "agents" in record
        assert "cost" in record
        assert len(record["agents"]) == 1
        assert record["agents"][0]["agent_id"] == "agent-1"
        assert record["agents"][0]["agent_name"] == "Scanner"

    def test_record_observed_cost(self) -> None:
        ledger = LLMUsageLedger()
        ledger.record_observed_cost(0.05)
        ledger.record_observed_cost(0.03)
        record = ledger.to_record()
        assert record["cost"] == pytest.approx(0.08, abs=1e-9)

    def test_record_observed_cost_ignores_negative(self) -> None:
        ledger = LLMUsageLedger()
        ledger.record_observed_cost(-1.0)
        record = ledger.to_record()
        assert record["cost"] == 0.0

    def test_hydrate_from_record(self) -> None:
        ledger = LLMUsageLedger()
        u = Usage()
        u.requests = 5
        u.input_tokens = 1000
        u.output_tokens = 500
        u.total_tokens = 1500
        ledger.record(agent_id="a1", usage=u, agent_name="Test", model="gpt-4o")
        ledger.record_observed_cost(0.10)

        record = ledger.to_record()

        new_ledger = LLMUsageLedger()
        new_ledger.hydrate(record)
        new_record = new_ledger.to_record()
        assert new_record["cost"] == pytest.approx(record["cost"], abs=1e-9)

    def test_hydrate_invalid_data(self) -> None:
        ledger = LLMUsageLedger()
        ledger.hydrate("not a dict")
        record = ledger.to_record()
        assert record["cost"] == 0.0
        assert record["agents"] == []
