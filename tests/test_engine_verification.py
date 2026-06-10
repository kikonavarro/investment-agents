"""
Tests de los fixes de fiabilidad de la verificación del motor (2026-06-11):

  1. DCFAssumptions valida RANGOS: un typo porcentaje-vs-fracción (8 en vez de 0.08)
     o un margen imposible lanzan ValueError con mensaje claro, nunca un fair value
     con cara de serio.
  2. _engine_fair_values NUNCA falla en silencio: devuelve (fvs, info) e info["reason"]
     explica el porqué de cada None (financiera, JSON roto, campo ausente, fuera de
     rango). Antes todos los casos devolvían None indistinguible — un caso legítimo
     (financiera) y un bug parecían lo mismo (mordió con MA/V).
  3. Las heurísticas de escala (peniques, acciones duales) y los overrides dejan
     RASTRO en info["notes"]; la zona gris del ratio (ni sano ni corregible) avisa.
  4. _sensitivity_grid y _implied_growth (reverse DCF): salidas puras del motor.
  5. Quality gate de beta: beta ausente/por defecto -> warning (el WACC por CAPM
     con beta inventada parece normal sin serlo).
"""
import json

import pytest

from tools import finalize_thesis as ft
from tools.quality_gates import validate_valuation
from tools.valuation_engine import DCFAssumptions


# --------------------------------------------------------------------------- #
# Helpers (mismo patrón que test_meta_overrides)
# --------------------------------------------------------------------------- #

def _sc(**overrides):
    sc = {
        "revenue_growth_y1": 0.05, "revenue_growth_y2": 0.05, "revenue_growth_y3": 0.05,
        "revenue_growth_y4": 0.05, "revenue_growth_y5": 0.05,
        "gross_margin": 0.40, "sga_pct": 0.15, "rd_pct": 0.05,
        "da_pct": 0.05, "capex_pct": 0.05, "tax_rate": 0.25,
        "wacc": 0.10, "terminal_multiple": 10.0,
    }
    sc.update(overrides)
    return sc


def _scenarios():
    return {"bear": _sc(), "base": _sc(), "bull": _sc()}


def _write_valuation(tmp_path, folder="X", *, revenue=1000e6, shares=100e6, price=10.0,
                     market_cap=None, total_debt=0, cash=0,
                     sector="Technology", industry="Software"):
    if market_cap is None:
        market_cap = price * shares
    val = {
        "sector": sector, "industry": industry,
        "current_price": price, "market_cap": market_cap, "shares_outstanding": shares,
        "latest_financials": {"revenue": revenue, "total_debt": total_debt, "cash": cash},
    }
    (tmp_path / f"{folder}_valuation.json").write_text(json.dumps(val), encoding="utf-8")
    return folder


def _assumptions(**overrides):
    params = dict(
        revenue_base=1000.0, revenue_growth=[0.05] * 5,
        gross_margin=0.40, sga_pct=0.15, rd_pct=0.05,
        da_pct=0.05, capex_pct=0.05, tax_rate=0.25,
        wacc=0.10, terminal_multiple=10.0,
    )
    params.update(overrides)
    return DCFAssumptions(**params)


# --------------------------------------------------------------------------- #
# 1. Validación de rangos del motor
# --------------------------------------------------------------------------- #

def test_motor_acepta_supuestos_sanos():
    assert _assumptions() is not None


@pytest.mark.parametrize("campo,valor,pista", [
    ("gross_margin", 1.5, "gross_margin"),     # >100%
    ("gross_margin", 0.0, "gross_margin"),     # margen bruto nulo no es DCF-able
    ("gross_margin", -0.2, "gross_margin"),
    ("sga_pct", -0.01, "sga_pct"),
    ("capex_pct", 1.2, "capex_pct"),           # CapEx > revenue todos los años
    ("tax_rate", 0.8, "tax_rate"),             # >60%
    ("tax_rate", -0.1, "tax_rate"),
    ("wacc", 10, "wacc"),                      # typo: 10 en vez de 0.10
    ("terminal_multiple", 80, "terminal_multiple"),  # >60x no defendible como terminal
])
def test_motor_rechaza_inputs_imposibles(campo, valor, pista):
    """Garbage in -> ValueError con el campo culpable, no un fair value."""
    with pytest.raises(ValueError, match=pista):
        _assumptions(**{campo: valor})


def test_motor_rechaza_growth_typo_porcentaje():
    """El typo clásico: 8 (800%) en vez de 0.08. Debe nombrar el año culpable."""
    with pytest.raises(ValueError, match="año 2"):
        _assumptions(revenue_growth=[0.05, 8, 0.05, 0.05, 0.05])


def test_motor_acepta_extremos_legitimos():
    """Bear agresivo (caída fuerte) y bull alto siguen siendo válidos: la validación
    caza lo IMPOSIBLE, no impone metodología."""
    _assumptions(revenue_growth=[-0.4, -0.2, 0.0, 0.02, 0.03], terminal_multiple=5)
    _assumptions(revenue_growth=[0.6, 0.5, 0.4, 0.3, 0.25], terminal_multiple=28,
                 wacc=0.14)


# --------------------------------------------------------------------------- #
# 2. Razones: ningún None silencioso
# --------------------------------------------------------------------------- #

def test_razon_sin_scenarios(tmp_path):
    fvs, info = ft._engine_fair_values({}, tmp_path, "X", None)
    assert fvs is None
    assert "scenarios" in info["reason"]


def test_razon_sin_valuation_json(tmp_path):
    fvs, info = ft._engine_fair_values(_scenarios(), tmp_path, "NOEXISTE", None)
    assert fvs is None
    assert "NOEXISTE_valuation.json" in info["reason"]


def test_razon_json_corrupto(tmp_path):
    (tmp_path / "X_valuation.json").write_text("{esto no es json", encoding="utf-8")
    fvs, info = ft._engine_fair_values(_scenarios(), tmp_path, "X", None)
    assert fvs is None
    assert "ilegible" in info["reason"]


def test_razon_financiera_explica_que_no_se_verifica(tmp_path):
    """El caso MA/V: sector financiero -> el motor NO verifica, y debe DECIRLO
    (antes devolvía None indistinguible de un bug)."""
    folder = _write_valuation(tmp_path, sector="Financial Services",
                              industry="Credit Services")
    fvs, info = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    assert fvs is None
    assert "Financial Services" in info["reason"]
    assert "NO quedan verificados" in info["reason"]


def test_razon_faltan_datos_empresa(tmp_path):
    folder = _write_valuation(tmp_path, revenue=0)
    fvs, info = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    assert fvs is None
    assert "revenue" in info["reason"]


def test_razon_escenario_campo_ausente(tmp_path):
    folder = _write_valuation(tmp_path)
    scenarios = _scenarios()
    del scenarios["bull"]["revenue_growth_y3"]
    fvs, info = ft._engine_fair_values(scenarios, tmp_path, folder, None)
    assert fvs is None
    assert "bull" in info["reason"] and "revenue_growth_y3" in info["reason"]


def test_razon_escenario_fuera_de_rango(tmp_path):
    """La validación del motor llega hasta la razón con el campo culpable."""
    folder = _write_valuation(tmp_path)
    scenarios = _scenarios()
    scenarios["bear"]["wacc"] = 10  # typo: 10 en vez de 0.10
    fvs, info = ft._engine_fair_values(scenarios, tmp_path, folder, None)
    assert fvs is None
    assert "bear" in info["reason"] and "wacc" in info["reason"]


def test_exito_reason_none_y_fvs_completos(tmp_path):
    folder = _write_valuation(tmp_path)
    fvs, info = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    assert fvs and set(fvs) == {"bear", "base", "bull"}
    assert info["reason"] is None


# --------------------------------------------------------------------------- #
# 3. Notas: heurísticas y overrides dejan rastro
# --------------------------------------------------------------------------- #

def test_nota_peniques(tmp_path):
    """ratio ~0.01 -> corrección GBp x100, y la nota lo cuenta."""
    folder = _write_valuation(tmp_path, price=1000.0, shares=100e6,
                              market_cap=1000.0 * 100e6 / 100)  # mcap en GBP, precio en GBp
    fvs, info = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    assert fvs is not None
    assert any("peniques" in n for n in info["notes"])


def test_nota_acciones_duales(tmp_path):
    folder = _write_valuation(tmp_path, shares=100e6, price=10.0, market_cap=3e9)  # ratio 3.0
    fvs, info = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    assert fvs is not None
    assert any("duales" in n for n in info["notes"])


def test_nota_zona_gris_del_ratio(tmp_path):
    """ratio 0.5: ni peniques (<0.02) ni dual (>1.5). Ninguna heurística corrige ->
    el fair value heredaría el error de escala. Debe avisar."""
    folder = _write_valuation(tmp_path, shares=100e6, price=10.0, market_cap=0.5e9)
    fvs, info = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    assert fvs is not None
    assert any("fuera de lo sano" in n for n in info["notes"])


def test_nota_overrides_dejan_rastro(tmp_path):
    folder = _write_valuation(tmp_path)
    fvs, info = ft._engine_fair_values(
        _scenarios(), tmp_path, folder,
        {"shares_override": 50e6, "net_debt_override_m": 100.0, "revenue_base_m": 2000.0})
    assert fvs is not None
    texto = " | ".join(info["notes"])
    assert "override de acciones" in texto
    assert "override de deuda neta" in texto
    assert "override de revenue base" in texto


def test_ratio_sano_sin_notas(tmp_path):
    folder = _write_valuation(tmp_path)  # ratio 1.0 exacto
    fvs, info = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    assert fvs is not None
    assert info["notes"] == []


# --------------------------------------------------------------------------- #
# 4. Sensibilidad y reverse DCF (puros)
# --------------------------------------------------------------------------- #

def _inputs(tmp_path, **kw):
    folder = _write_valuation(tmp_path, **kw)
    inputs, info = ft._dcf_inputs(tmp_path, folder, None)
    assert inputs is not None, info["reason"]
    return inputs


def test_sensibilidad_3x3_monotona(tmp_path):
    inputs = _inputs(tmp_path)
    sens = ft._sensitivity_grid(_sc(), inputs)
    assert sens is not None
    assert len(sens["grid"]) == 3 and all(len(r) == 3 for r in sens["grid"])
    centro = sens["grid"][1][1]
    fvs, _ = ft._engine_fair_values(_scenarios(), tmp_path, "X", None)
    assert centro == pytest.approx(fvs["base"], rel=1e-9)   # celda central = FV base
    # Más WACC -> menos FV (misma columna); más múltiplo -> más FV (misma fila).
    assert sens["grid"][0][1] > centro > sens["grid"][2][1]
    assert sens["grid"][1][0] < centro < sens["grid"][1][2]


def test_sensibilidad_escenario_incompleto_es_none(tmp_path):
    inputs = _inputs(tmp_path)
    assert ft._sensitivity_grid({}, inputs) is None


def test_reverse_dcf_recupera_el_growth(tmp_path):
    """Si el precio ES el fair value del base, el growth implícito debe ser ~el del base."""
    folder = _write_valuation(tmp_path)
    fvs, _ = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    inputs, _ = ft._dcf_inputs(tmp_path, folder, None)
    inputs["price"] = fvs["base"]
    g = ft._implied_growth(_sc(), inputs)
    assert g == pytest.approx(0.05, abs=1e-4)


def test_reverse_dcf_precio_mayor_implica_mas_growth(tmp_path):
    folder = _write_valuation(tmp_path)
    fvs, _ = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    inputs, _ = ft._dcf_inputs(tmp_path, folder, None)
    inputs["price"] = fvs["base"] * 1.5
    g = ft._implied_growth(_sc(), inputs)
    assert g is not None and g > 0.05


def test_reverse_dcf_fuera_de_rango_es_none(tmp_path):
    """Precio inalcanzable con g <= 100% -> None (revisar método), no un número falso."""
    folder = _write_valuation(tmp_path)
    inputs, _ = ft._dcf_inputs(tmp_path, folder, None)
    inputs["price"] = 1e9
    assert ft._implied_growth(_sc(), inputs) is None


def test_reverse_dcf_sin_precio_es_none(tmp_path):
    inputs = _inputs(tmp_path)
    inputs["price"] = 0
    assert ft._implied_growth(_sc(), inputs) is None


# --------------------------------------------------------------------------- #
# 5. Quality gate de beta
# --------------------------------------------------------------------------- #

def _valuation_base():
    """Valuation mínimo que pasa los checks (precio, revenue, histórico, shares)."""
    return {
        "current_price": 100.0,
        "shares_outstanding": 100e6,
        "historical_years": [2022, 2023, 2024],
        "latest_financials": {"revenue": 1000e6, "gross_margin": 0.4,
                              "operating_margin": 0.2, "total_debt": 0, "cash": 0},
        "reference_metrics": {"beta": 1.1, "beta_is_default": False},
    }


def test_gate_beta_real_no_avisa():
    result = validate_valuation(_valuation_base())
    assert not any(w["check"] == "beta" for w in result["warnings"])


def test_gate_beta_por_defecto_avisa():
    v = _valuation_base()
    v["reference_metrics"]["beta_is_default"] = True
    result = validate_valuation(v)
    avisos = [w for w in result["warnings"] if w["check"] == "beta"]
    assert len(avisos) == 1 and avisos[0]["level"] == "warning"
    assert "1.0 por defecto" in avisos[0]["message"]


def test_gate_beta_ausente_avisa():
    v = _valuation_base()
    v["reference_metrics"]["beta"] = None
    v["reference_metrics"]["beta_is_default"] = False
    result = validate_valuation(v)
    assert any(w["check"] == "beta" for w in result["warnings"])
