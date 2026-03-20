"""Tests para tools/formatters.py"""
from tools.formatters import (
    format_portfolio_for_llm,
    format_screener_results_for_llm,
    _format_large_number,
    _series_to_arrow,
)


def test_format_large_number_trillions():
    assert _format_large_number(2.5e12) == "$2.5T"


def test_format_large_number_billions():
    assert _format_large_number(394e9) == "$394B"


def test_format_large_number_millions():
    assert _format_large_number(50e6) == "$50M"


def test_format_large_number_small():
    assert _format_large_number(1234) == "$1,234"


def test_series_to_arrow():
    data = {"2020": 100, "2021": 120, "2022": 150}
    result = _series_to_arrow(data)
    assert result == "100→120→150"


def test_series_to_arrow_with_divisor():
    data = {"2020": 100e9, "2021": 120e9}
    result = _series_to_arrow(data, divisor=1e9)
    assert result == "100→120"


def test_portfolio_empty():
    result = format_portfolio_for_llm([])
    assert result == "CARTERA VACÍA"


def test_portfolio_with_positions():
    positions = [
        {"name": "Apple Inc", "current": 10000, "invested": 8000, "pnl_pct": 25.0},
        {"name": "Microsoft", "current": 5000, "invested": 5500, "pnl_pct": -9.1},
    ]
    result = format_portfolio_for_llm(positions)
    assert "2 posiciones" in result
    assert "Apple" in result
    assert "Microsoft" in result


def test_portfolio_manual_source():
    positions = [
        {"name": "Fondo Test", "current": 1000, "invested": 900, "pnl_pct": 11.1, "source": "manual"},
    ]
    result = format_portfolio_for_llm(positions)
    assert "manual" in result


def test_screener_empty():
    result = format_screener_results_for_llm([])
    assert "0 candidatas" in result


def test_screener_with_candidates():
    candidates = [
        {"ticker": "AAPL", "sector": "Technology", "pe": 15.2, "pb": 2.1,
         "de": 1.8, "fcf_yield": 0.035, "roic": 0.45},
        {"ticker": "JNJ", "sector": "Healthcare", "pe": 12.0, "pb": 1.5,
         "de": 0.5, "fcf_yield": 0.05, "roic": 0.25},
    ]
    result = format_screener_results_for_llm(candidates)
    assert "2 candidatas" in result
    assert "AAPL" in result
    assert "JNJ" in result


def test_screener_missing_values():
    candidates = [
        {"ticker": "XYZ", "sector": "N/A", "pe": None, "pb": None,
         "de": None, "fcf_yield": None, "roic": None},
    ]
    result = format_screener_results_for_llm(candidates)
    assert "XYZ" in result
    assert "N/A" in result
