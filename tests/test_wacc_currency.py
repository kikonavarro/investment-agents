"""Tests para WACC por divisa/mercado (Fase 1C)."""
from config.settings import WACC_DEFAULTS


def test_wacc_defaults_has_all_major_currencies():
    rates = WACC_DEFAULTS["risk_free_rates"]
    for currency in ["USD", "EUR", "GBP", "CAD", "CHF", "JPY"]:
        assert currency in rates, f"Falta {currency} en risk_free_rates"


def test_wacc_defaults_has_default():
    assert "default" in WACC_DEFAULTS["risk_free_rates"]
    assert "default" in WACC_DEFAULTS["equity_risk_premiums"]


def test_risk_free_rates_reasonable():
    for currency, rate in WACC_DEFAULTS["risk_free_rates"].items():
        if currency == "default":
            continue
        assert 0 <= rate <= 0.15, f"{currency}: risk-free rate {rate} fuera de rango"


def test_erp_reasonable():
    for currency, erp in WACC_DEFAULTS["equity_risk_premiums"].items():
        if currency == "default":
            continue
        assert 0.03 <= erp <= 0.12, f"{currency}: ERP {erp} fuera de rango"


def test_credit_spread_exists():
    assert "credit_spread" in WACC_DEFAULTS
    assert 0.01 <= WACC_DEFAULTS["credit_spread"] <= 0.05


def test_emerging_markets_higher_rates():
    rates = WACC_DEFAULTS["risk_free_rates"]
    # Emergentes deben tener rates más altos que desarrollados
    assert rates["BRL"] > rates["USD"]
    assert rates["INR"] > rates["EUR"]
    assert rates["MXN"] > rates["GBP"]
