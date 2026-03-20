"""Tests para agents/base.py — tracker y lógica pura (sin API)."""
from agents.base import (
    reset_tracker,
    _log_call,
    get_tracker_summary,
    _should_retry,
    AgentError,
    COST_PER_M_TOKENS,
)
import anthropic


def test_tracker_reset():
    reset_tracker()
    _log_call("quick", "test-model", 100, 50, 1.0, "test")
    assert get_tracker_summary()["calls"] == 1
    reset_tracker()
    assert get_tracker_summary()["calls"] == 0


def test_tracker_accumulates():
    reset_tracker()
    _log_call("quick", "model-a", 100, 50, 1.0, "agent_a")
    _log_call("standard", "model-b", 500, 200, 2.5, "agent_b")
    s = get_tracker_summary()
    assert s["calls"] == 2
    assert s["input_tokens"] == 600
    assert s["output_tokens"] == 250
    assert s["total_tokens"] == 850
    assert s["total_duration_s"] == 3.5


def test_tracker_cost_calculation():
    reset_tracker()
    # 1000 input + 500 output con Haiku ($1/$5 por M)
    _log_call("quick", "haiku", 1000, 500, 1.0, "test")
    s = get_tracker_summary()
    expected = (1000 * 1.0 + 500 * 5.0) / 1_000_000  # $0.0035
    assert abs(s["total_cost_usd"] - expected) < 0.0001


def test_tracker_detail_entries():
    reset_tracker()
    _log_call("standard", "sonnet", 200, 100, 1.5, "thesis_writer")
    s = get_tracker_summary()
    assert len(s["detail"]) == 1
    entry = s["detail"][0]
    assert entry["agent"] == "thesis_writer"
    assert entry["tier"] == "standard"
    assert entry["input_tokens"] == 200
    assert entry["output_tokens"] == 100


def test_agent_error_attributes():
    e = AgentError("test error", agent_name="analyst", tier="standard")
    assert str(e) == "test error"
    assert e.agent_name == "analyst"
    assert e.tier == "standard"


def test_cost_tiers_defined():
    assert "quick" in COST_PER_M_TOKENS
    assert "standard" in COST_PER_M_TOKENS
    assert "deep" in COST_PER_M_TOKENS
    for tier, (cost_in, cost_out) in COST_PER_M_TOKENS.items():
        assert cost_in > 0
        assert cost_out > 0
        assert cost_out > cost_in  # Output siempre más caro
