"""Tests para tools/quality_gates.py"""
from tools.quality_gates import validate_valuation


def test_good_data_high_confidence(good_valuation):
    result = validate_valuation(good_valuation)
    assert result["confidence"] == "high"
    assert result["failed"] == 0
    assert len(result["warnings"]) == 0


def test_bad_data_low_confidence(bad_valuation):
    result = validate_valuation(bad_valuation)
    assert result["confidence"] == "low"
    assert result["failed"] > 0
    criticals = [w for w in result["warnings"] if w["level"] == "critical"]
    assert len(criticals) >= 2


def test_zero_price_is_critical():
    v = _minimal(current_price=0)
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "precio" in checks


def test_zero_revenue_is_critical():
    v = _minimal(revenue=0)
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "revenue" in checks


def test_negative_gross_margin_warns():
    v = _minimal(gross_margin=-0.2)
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "margen_bruto" in checks


def test_wacc_no_check_on_raw_data():
    """WACC/TV checks se eliminaron de quality_gates (ahora solo valida datos crudos)."""
    v = _minimal(wacc=0.30)
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "wacc" not in checks  # No hay check de WACC en datos crudos


def test_terminal_multiple_no_check_on_raw_data():
    """TV check se eliminó de quality_gates (ahora solo valida datos crudos)."""
    v = _minimal(terminal_multiple=50)
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "terminal_multiple" not in checks  # No hay check de TV en datos crudos


def test_few_years_warns():
    v = _minimal(historical_years=[2025])
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "historico" in checks


def test_high_debt_warns():
    v = _minimal(total_debt=60_000_000, total_equity=1_000_000)
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "deuda" in checks


def test_negative_equity_warns():
    v = _minimal(total_equity=-100_000)
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "patrimonio" in checks


def test_medium_confidence_one_critical():
    v = _minimal(current_price=0)  # 1 critical
    result = validate_valuation(v)
    assert result["confidence"] in ("medium", "low")


# --- Helper ---

def _minimal(**overrides):
    """Crea una valoración mínima válida con overrides."""
    base = {
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
            "base": {"wacc": 0.10, "terminal_multiple": 15},
        },
        "historical_years": [2022, 2023, 2024, 2025],
    }
    # Aplicar overrides
    for k, v in overrides.items():
        if k in ("revenue", "gross_margin", "operating_margin", "total_debt", "total_equity"):
            base["latest_financials"][k] = v
        elif k in ("wacc", "terminal_multiple"):
            base["scenarios"]["base"][k] = v
        else:
            base[k] = v
    return base
