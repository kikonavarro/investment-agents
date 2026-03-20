"""Tests para tools/screener_engine.py — solo lógica pura (sin red)."""
from tools.screener_engine import _passes_filters, _calc_score, _load_filters


def test_passes_filters_all_ok():
    data = {"pe": 10, "pb": 1.2, "current_ratio": 2.0, "de": 50, "fcf_yield": 0.08}
    filters = {"pe_ratio_max": 15, "pb_ratio_max": 2.0, "current_ratio_min": 1.5}
    assert _passes_filters(data, filters) is True


def test_fails_pe_filter():
    data = {"pe": 20, "pb": 1.0}
    filters = {"pe_ratio_max": 15}
    assert _passes_filters(data, filters) is False


def test_fails_pb_filter():
    data = {"pe": 10, "pb": 3.5}
    filters = {"pb_ratio_max": 2.0}
    assert _passes_filters(data, filters) is False


def test_fails_current_ratio():
    data = {"current_ratio": 0.8}
    filters = {"current_ratio_min": 1.5}
    assert _passes_filters(data, filters) is False


def test_none_values_pass():
    """Si un dato es None, no penalizar."""
    data = {"pe": None, "pb": None, "current_ratio": None}
    filters = {"pe_ratio_max": 15, "pb_ratio_max": 2.0}
    assert _passes_filters(data, filters) is True


def test_pe_times_pb_filter():
    data = {"pe": 10, "pb": 3.0}
    filters = {"pe_times_pb_max": 22}
    assert _passes_filters(data, filters) is False

    data2 = {"pe": 10, "pb": 2.0}
    assert _passes_filters(data2, filters) is True


def test_debt_filter_percentage():
    """yfinance devuelve D/E en %, filtro en ratio."""
    data = {"de": 150}  # 150% = 1.5x
    filters = {"debt_to_equity_max": 1.0}  # max 1.0x = 100%
    assert _passes_filters(data, filters) is False

    data2 = {"de": 80}
    assert _passes_filters(data2, filters) is True


def test_calc_score_basic():
    data = {"fcf_yield": 0.08, "pe": 10, "pb": 1.0, "dividend_yield": 0.03}
    filters = {}
    score = _calc_score(data, filters)
    assert score > 0
    # fcf_yield*100=8 + (20-10)=10 + (3-1)=2 + 0.03*50=1.5 = 21.5
    assert abs(score - 21.5) < 0.1


def test_calc_score_no_data():
    data = {}
    score = _calc_score(data, {})
    assert score == 0


def test_load_filters_graham():
    filters = _load_filters("graham_default")
    assert isinstance(filters, dict)
    assert len(filters) > 0


def test_load_filters_nonexistent():
    filters = _load_filters("nonexistent_filter_xyz")
    assert filters == {} or filters is None
