"""Tests para format_comparison_for_llm (Fase 3E)."""
from tools.formatters import format_comparison_for_llm


def test_comparison_header(good_valuation):
    val2 = {**good_valuation, "ticker": "MSFT", "company": "Microsoft Corp."}
    result = format_comparison_for_llm(good_valuation, val2)
    assert "AAPL" in result
    assert "MSFT" in result
    assert "COMPARACIÓN" in result


def test_comparison_has_financials(good_valuation):
    val2 = {**good_valuation, "ticker": "MSFT"}
    result = format_comparison_for_llm(good_valuation, val2)
    assert "Revenue" in result
    assert "Margen bruto" in result
    assert "WACC" in result


def test_comparison_has_scenarios(good_valuation):
    val2 = {**good_valuation, "ticker": "MSFT"}
    result = format_comparison_for_llm(good_valuation, val2)
    assert "Bear" in result
    assert "Base" in result
    assert "Bull" in result


def test_comparison_with_minimal_data():
    v1 = {"ticker": "A", "latest_financials": {"revenue": 1e9}, "scenarios": {}}
    v2 = {"ticker": "B", "latest_financials": {"revenue": 2e9}, "scenarios": {}}
    result = format_comparison_for_llm(v1, v2)
    assert "A" in result
    assert "B" in result
