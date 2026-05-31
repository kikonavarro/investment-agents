"""
Tests del motor de valoración (tools/valuation_engine.py).

Fijan la metodología correcta y protegen contra los bugs históricos:
  - EBIT ≠ EBITDA (EBITDA = EBIT + D&A)
  - Terminal Value sobre EBITDA, no sobre EBIT
  - UFCF = EBIT×(1−T) + D&A − CapEx (no restar D&A dos veces)
"""

import pytest

from tools.valuation_engine import (
    DCFAssumptions,
    run_dcf,
    run_three_scenarios,
    calculate_wacc_capm,
    WEIGHT_BEAR,
    WEIGHT_BASE,
    WEIGHT_BULL,
)


def _simple_assumptions(**overrides) -> DCFAssumptions:
    """Escenario base con números elegidos para dar resultados redondos."""
    params = dict(
        revenue_base=1000.0,
        revenue_growth=[0.10, 0.10, 0.10, 0.10, 0.10],
        gross_margin=0.50,
        sga_pct=0.20,
        rd_pct=0.0,
        da_pct=0.05,
        capex_pct=0.05,
        tax_rate=0.25,
        wacc=0.10,
        terminal_multiple=10.0,
    )
    params.update(overrides)
    return DCFAssumptions(**params)


# ─────────────────────────── GOLDEN TEST ───────────────────────────

def test_golden_case_valores_calculados_a_mano():
    """
    Caso con aritmética verificable a mano:
      ebit_margin = 0.50 − 0.20 − 0 = 0.30
      Como capex_pct == da_pct, UFCF_t = EBIT_t×0.75 = revenue_t×0.225,
      y al descontar a la misma tasa que crece (10%), cada PV(UFCF) = 225.
      pv_ufcf_sum = 225 × 5 = 1125
      EBITDA_5 = 1000×1.1^5 × 0.35 = 563.6785 ; TV = ×10 = 5636.785
      PV(TV) = 5636.785 / 1.1^5 = 3500
      EV = 1125 + 3500 = 4625 ; equity = 4625 ; FV/acción = 4625/100 = 46.25
    """
    r = run_dcf(_simple_assumptions(), net_debt=0.0, shares_outstanding=100.0)

    assert r.pv_ufcf_sum == pytest.approx(1125.0, rel=1e-9)
    assert r.pv_terminal_value == pytest.approx(3500.0, rel=1e-9)
    assert r.enterprise_value == pytest.approx(4625.0, rel=1e-9)
    assert r.equity_value == pytest.approx(4625.0, rel=1e-9)
    assert r.fair_value_per_share == pytest.approx(46.25, rel=1e-9)


def test_net_debt_reduce_equity():
    """La deuda neta se resta del EV para llegar al equity."""
    r = run_dcf(_simple_assumptions(), net_debt=625.0, shares_outstanding=100.0)
    assert r.equity_value == pytest.approx(4000.0, rel=1e-9)   # 4625 − 625
    assert r.fair_value_per_share == pytest.approx(40.0, rel=1e-9)


# ───────────────────── REGRESIÓN: BUGS HISTÓRICOS ─────────────────────

def test_ebitda_es_ebit_mas_da():
    """EBITDA = EBIT + D&A. Nunca EBIT solo (bug histórico)."""
    r = run_dcf(_simple_assumptions(da_pct=0.05), net_debt=0.0, shares_outstanding=100.0)
    for y in r.years:
        assert y.ebitda == pytest.approx(y.ebit + y.da, rel=1e-12)
        assert y.ebitda > y.ebit  # con D&A > 0, EBITDA estrictamente mayor


def test_terminal_value_sobre_ebitda_no_ebit():
    """El TV se calcula sobre EBITDA del último año, no sobre EBIT."""
    a = _simple_assumptions(da_pct=0.05)
    r = run_dcf(a, net_debt=0.0, shares_outstanding=100.0)
    ebitda_final = r.years[-1].ebitda
    ebit_final = r.years[-1].ebit
    assert r.terminal_value == pytest.approx(ebitda_final * a.terminal_multiple, rel=1e-12)
    # Y NO coincide con usar EBIT (prueba de que no se confunden)
    assert r.terminal_value != pytest.approx(ebit_final * a.terminal_multiple, rel=1e-6)


def test_ufcf_no_resta_da_dos_veces():
    """UFCF = EBIT×(1−T) + D&A − CapEx. Verificación término a término."""
    a = _simple_assumptions(da_pct=0.08, capex_pct=0.03, tax_rate=0.21)
    r = run_dcf(a, net_debt=0.0, shares_outstanding=100.0)
    for y in r.years:
        esperado = y.ebit * (1 - a.tax_rate) + y.da - y.capex
        assert y.ufcf == pytest.approx(esperado, rel=1e-12)


def test_mas_da_sube_fair_value_via_terminal_value():
    """
    Subir D&A manteniendo UFCF constante (capex sigue a da) DEBE subir el fair value,
    porque el EBITDA —y por tanto el Terminal Value— crece. Si el TV usara EBIT,
    el fair value no cambiaría. Esto ancla que el TV depende de EBITDA.
    """
    bajo = run_dcf(_simple_assumptions(da_pct=0.05, capex_pct=0.05),
                   net_debt=0.0, shares_outstanding=100.0)
    alto = run_dcf(_simple_assumptions(da_pct=0.10, capex_pct=0.10),
                   net_debt=0.0, shares_outstanding=100.0)
    # UFCF idéntico (da − capex = 0 en ambos), pero EBITDA mayor en 'alto'
    assert alto.years[-1].ufcf == pytest.approx(bajo.years[-1].ufcf, rel=1e-9)
    assert alto.years[-1].ebitda > bajo.years[-1].ebitda
    assert alto.fair_value_per_share > bajo.fair_value_per_share


def test_descuento_correcto_por_anno():
    """discount_factor del año t = 1/(1+wacc)^t."""
    a = _simple_assumptions(wacc=0.12)
    r = run_dcf(a, net_debt=0.0, shares_outstanding=100.0)
    for y in r.years:
        assert y.discount_factor == pytest.approx(1 / (1 + a.wacc) ** y.year, rel=1e-12)
        assert y.pv_ufcf == pytest.approx(y.ufcf * y.discount_factor, rel=1e-12)


# ─────────────────────── PONDERACIÓN 40/40/20 ───────────────────────

def test_ponderacion_40_40_20():
    """El fair value ponderado = 0.4·bear + 0.4·base + 0.2·bull."""
    bear = _simple_assumptions(revenue_growth=[0.02] * 5, terminal_multiple=8.0)
    base = _simple_assumptions(revenue_growth=[0.06] * 5, terminal_multiple=10.0)
    bull = _simple_assumptions(revenue_growth=[0.12] * 5, terminal_multiple=13.0)

    out = run_three_scenarios(bear, base, bull, net_debt=0.0, shares_outstanding=100.0)
    fv = {k: out["scenarios"][k].fair_value_per_share for k in ("bear", "base", "bull")}
    esperado = WEIGHT_BEAR * fv["bear"] + WEIGHT_BASE * fv["base"] + WEIGHT_BULL * fv["bull"]

    assert out["weighted_fair_value"] == pytest.approx(esperado, rel=1e-12)
    assert fv["bear"] < fv["base"] < fv["bull"]  # orden esperado
    assert (WEIGHT_BEAR + WEIGHT_BASE + WEIGHT_BULL) == pytest.approx(1.0)


# ─────────────────────────── WACC (CAPM) ───────────────────────────

def test_wacc_capm_aplica_suelo():
    """Beta baja -> CAPM por debajo del 10% -> se aplica el suelo del 10%."""
    assert calculate_wacc_capm(beta=1.0, risk_free_rate=0.04, equity_risk_premium=0.055) == pytest.approx(0.10)


def test_wacc_capm_sin_suelo_cuando_supera_minimo():
    """Beta alta -> CAPM por encima del suelo -> se respeta el valor calculado."""
    assert calculate_wacc_capm(beta=2.0, risk_free_rate=0.04, equity_risk_premium=0.055) == pytest.approx(0.15)


# ─────────────────────── VALIDACIONES / CASOS LÍMITE ───────────────────────

@pytest.mark.parametrize("kwargs", [
    {"revenue_base": 0.0},
    {"revenue_base": -100.0},
    {"wacc": 0.0},
    {"terminal_multiple": 0.0},
    {"revenue_growth": []},
])
def test_assumptions_invalidas_lanzan_error(kwargs):
    with pytest.raises(ValueError):
        _simple_assumptions(**kwargs)


def test_shares_cero_lanza_error():
    with pytest.raises(ValueError):
        run_dcf(_simple_assumptions(), net_debt=0.0, shares_outstanding=0.0)


def test_equity_negativo_no_se_oculta():
    """
    Empresa muy apalancada (net_debt > EV): el equity sale negativo y el motor
    NO lo enmascara. La interpretación económica (suelo por responsabilidad
    limitada) es responsabilidad de la capa de análisis, no del motor.
    """
    r = run_dcf(_simple_assumptions(), net_debt=10_000.0, shares_outstanding=100.0)
    assert r.equity_value < 0
    assert r.fair_value_per_share < 0


def test_tv_weight_pct_coherente():
    """El peso del TV es PV(TV)/EV·100 y queda en el caso golden ≈ 75.7%."""
    r = run_dcf(_simple_assumptions(), net_debt=0.0, shares_outstanding=100.0)
    assert r.tv_weight_pct == pytest.approx(3500.0 / 4625.0 * 100, rel=1e-9)
    assert 0 < r.tv_weight_pct < 100
