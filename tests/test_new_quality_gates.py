"""Tests para los 4 quality gates nuevos (Fase 1B)."""
from tools.quality_gates import validate_valuation


def _minimal(**overrides):
    """Valoración mínima válida con overrides."""
    base = {
        "ticker": "TEST",
        "current_price": 100.0,
        "shares_outstanding": 1_000_000,
        "latest_financials": {
            "revenue": 50_000_000,
            "gross_margin": 0.40,
            "operating_margin": 0.20,
            "total_debt": 1_000_000,
            "total_equity": 5_000_000,
        },
        "scenarios": {
            "bear": {"wacc": 0.12, "terminal_multiple": 10, "revenue_growth_y1": 0.02},
            "base": {"wacc": 0.10, "terminal_multiple": 15, "revenue_growth_y1": 0.07},
            "bull": {"wacc": 0.09, "terminal_multiple": 18, "revenue_growth_y1": 0.12},
        },
        "historical_years": [2022, 2023, 2024, 2025],
    }
    for k, v in overrides.items():
        if k in ("revenue", "gross_margin", "operating_margin", "total_debt", "total_equity"):
            base["latest_financials"][k] = v
        elif k.startswith("bear_") or k.startswith("base_") or k.startswith("bull_"):
            scenario, field = k.split("_", 1)
            base["scenarios"][scenario][field] = v
        else:
            base[k] = v
    return base


# --- Test _check_negative_fair_value ---

def test_negative_fair_value_not_triggered_on_normal():
    v = _minimal()
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "fair_value_negativo" not in checks


# --- Test _check_revenue_decline_base ---

def test_revenue_decline_base_detected():
    v = _minimal()
    v["scenarios"]["base"]["revenue_growth_y1"] = -0.05
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "revenue_decline_base" in checks


def test_revenue_growth_positive_no_warning():
    v = _minimal()
    v["scenarios"]["base"]["revenue_growth_y1"] = 0.05
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "revenue_decline_base" not in checks


# --- Test _check_wacc_range_by_market ---

def test_wacc_too_low_warns():
    v = _minimal()
    v["scenarios"]["base"]["wacc"] = 0.03  # <5% para mercado desarrollado
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "wacc_rango_mercado" in checks


def test_wacc_too_high_warns():
    v = _minimal()
    v["scenarios"]["base"]["wacc"] = 0.20  # >18%
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "wacc_rango_mercado" in checks


def test_wacc_normal_no_warning():
    v = _minimal()
    v["scenarios"]["base"]["wacc"] = 0.10  # Normal
    result = validate_valuation(v)
    wacc_range_warnings = [w for w in result["warnings"] if w["check"] == "wacc_rango_mercado"]
    assert len(wacc_range_warnings) == 0


# --- Test total_checks updated ---

def test_total_checks_is_17():
    v = _minimal()
    result = validate_valuation(v)
    assert result["passed"] + result["failed"] == 17
