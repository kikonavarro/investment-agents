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
    assert "EBITDA" in result
    assert "FCF" in result


def test_comparison_has_reference_metrics(good_valuation):
    """El JSON crudo no contiene escenarios — el formatter expone métricas de referencia."""
    val2 = {**good_valuation, "ticker": "MSFT"}
    val2["reference_metrics"] = {"ev_ebitda": 18.5, "avg_growth": 0.08, "beta": 1.1}
    val1 = {**good_valuation, "reference_metrics": {"ev_ebitda": 22.0, "avg_growth": 0.06, "beta": 1.2}}
    result = format_comparison_for_llm(val1, val2)
    assert "EV/EBITDA" in result
    assert "Avg Growth" in result
    assert "Beta" in result


def test_comparison_with_minimal_data():
    v1 = {"ticker": "A", "latest_financials": {"revenue": 1e9}}
    v2 = {"ticker": "B", "latest_financials": {"revenue": 2e9}}
    result = format_comparison_for_llm(v1, v2)
    assert "A" in result
    assert "B" in result
