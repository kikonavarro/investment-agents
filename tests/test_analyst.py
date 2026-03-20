"""Tests para agents/analyst.py — funciones puras (sin red/API)."""
import json
import shutil
from pathlib import Path
from agents.analyst import (
    _clean_ticker,
    _is_us_ticker,
    _get_currency_symbol,
    _summarize_year,
    _save_versioned,
    load_history,
    load_valuation,
)
from config.settings import VALUATIONS_DIR


def test_clean_ticker():
    assert _clean_ticker("AAPL") == "AAPL"
    assert _clean_ticker("ITX.MC") == "ITX_MC"
    assert _clean_ticker("WOSG.L") == "WOSG_L"


def test_is_us_ticker():
    assert _is_us_ticker("AAPL") is True
    assert _is_us_ticker("MSFT") is True
    assert _is_us_ticker("ITX.MC") is False
    assert _is_us_ticker("BATS.L") is False


def test_currency_symbol():
    assert _get_currency_symbol("AAPL") == "$"
    assert _get_currency_symbol("ITX.MC") == "EUR "
    assert _get_currency_symbol("BATS.L") == "GBP "
    assert _get_currency_symbol("RY.TO") == "C$"
    assert _get_currency_symbol("BHP.AX") == "A$"


def test_summarize_year():
    data = {
        "total_revenue": 394e9,
        "net_income": 97e9,
        "ebitda": 130e9,
        "free_cashflow": 99e9,
        "operating_income": 118e9,
        "extra_field": "ignored",
    }
    result = _summarize_year(data)
    assert result["revenue"] == 394e9
    assert result["net_income"] == 97e9
    assert result["fcf"] == 99e9
    assert "extra_field" not in result


def test_summarize_year_missing_fields():
    result = _summarize_year({})
    assert result["revenue"] == 0
    assert result["fcf"] == 0


class TestVersioning:
    """Tests de versionado — usan directorio temporal."""

    def setup_method(self):
        self.test_dir = VALUATIONS_DIR / "_TEST_VERSION"
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_save_versioned_creates_file(self):
        v = {"date": "2026-03-20", "current_price": 150, "currency": "$",
             "latest_financials": {"revenue": 50e9, "gross_margin": 0.4},
             "scenarios": {"base": {"wacc": 0.1, "revenue_growth_y1": 0.07,
                                    "terminal_multiple": 15},
                           "bear": {"wacc": 0.12}, "bull": {"wacc": 0.08}}}
        _save_versioned(self.test_dir, "_TEST_VERSION", v)

        # Debe existir archivo con timestamp
        versioned = list(self.test_dir.glob("*_20*_valuation.json"))
        assert len(versioned) == 1

        # Debe existir history.json
        history_path = self.test_dir / "history.json"
        assert history_path.exists()

    def test_history_accumulates(self):
        for date, price in [("2026-01-10", 140), ("2026-02-15", 145), ("2026-03-20", 155)]:
            v = {"date": date, "current_price": price, "currency": "$",
                 "latest_financials": {"revenue": 50e9, "gross_margin": 0.4},
                 "scenarios": {"base": {"wacc": 0.1, "revenue_growth_y1": 0.07,
                                        "terminal_multiple": 15},
                               "bear": {"wacc": 0.12}, "bull": {"wacc": 0.08}}}
            _save_versioned(self.test_dir, "_TEST_VERSION", v)

        history = json.loads((self.test_dir / "history.json").read_text())
        assert len(history) == 3
        assert history[0]["date"] == "2026-01-10"
        assert history[2]["date"] == "2026-03-20"

    def test_same_day_replaces(self):
        v1 = {"date": "2026-03-20", "current_price": 150, "currency": "$",
              "latest_financials": {"revenue": 50e9, "gross_margin": 0.4},
              "scenarios": {"base": {"wacc": 0.1, "revenue_growth_y1": 0.07,
                                     "terminal_multiple": 15},
                            "bear": {"wacc": 0.12}, "bull": {"wacc": 0.08}}}
        _save_versioned(self.test_dir, "_TEST_VERSION", v1)

        v2 = {**v1, "current_price": 155}
        _save_versioned(self.test_dir, "_TEST_VERSION", v2)

        history = json.loads((self.test_dir / "history.json").read_text())
        assert len(history) == 1
        assert history[0]["current_price"] == 155


def test_load_history_nonexistent():
    result = load_history("NONEXISTENT_TICKER_XYZ_999")
    assert result == []


def test_load_valuation_nonexistent():
    result = load_valuation("NONEXISTENT_TICKER_XYZ_999")
    assert result is None
