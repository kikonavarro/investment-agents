"""Tests para quality gates: checks de segmentos y shares crossvalidation."""
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
        "historical_years": [2022, 2023, 2024, 2025],
        "segments": [{"name": "Principal", "revenues": {}}],
    }
    for k, v in overrides.items():
        if k in ("revenue", "gross_margin", "operating_margin", "total_debt", "total_equity"):
            base["latest_financials"][k] = v
        else:
            base[k] = v
    return base


# --- Test _check_segments_suspicious ---

def test_segments_suspicious_large_company():
    """Empresa >$50B revenue con 1 segmento → warning."""
    v = _minimal(revenue=100_000_000_000)
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "segmentos_sospechosos" in checks


def test_segments_ok_small_company():
    """Empresa <$50B revenue con 1 segmento → sin warning."""
    v = _minimal(revenue=10_000_000_000)
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "segmentos_sospechosos" not in checks


def test_segments_ok_multiple():
    """Empresa grande con >1 segmento → sin warning."""
    v = _minimal(revenue=100_000_000_000)
    v["segments"] = [
        {"name": "Seg A", "revenues": {}},
        {"name": "Seg B", "revenues": {}},
    ]
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "segmentos_sospechosos" not in checks


# --- Test _check_shares_crossvalidation ---

def test_shares_divergence_warns():
    """sharesOutstanding vs DilutedAverageShares divergen >5% → warning."""
    v = _minimal()
    v["shares_outstanding"] = 1_000_000
    v["diluted_avg_shares"] = 1_200_000  # 20% más
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "shares_divergencia" in checks


def test_shares_similar_ok():
    """sharesOutstanding vs DilutedAverageShares difieren <5% → sin warning."""
    v = _minimal()
    v["shares_outstanding"] = 1_000_000
    v["diluted_avg_shares"] = 1_030_000  # 3% más
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "shares_divergencia" not in checks


def test_shares_no_diluted_data_ok():
    """Sin diluted_avg_shares → no salta (no hay dato para comparar)."""
    v = _minimal()
    result = validate_valuation(v)
    checks = {w["check"] for w in result["warnings"]}
    assert "shares_divergencia" not in checks


# --- Test total_checks ---

def test_total_checks_is_11():
    v = _minimal()
    result = validate_valuation(v)
    assert result["passed"] + result["failed"] == 11
