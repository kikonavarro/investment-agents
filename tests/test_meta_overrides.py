"""
Tests del esquema canónico de overrides de la tesis (_meta) y de que la
verificación del motor (finalize_thesis._engine_fair_values) los respeta IGUAL
que el Excel.

Cubren:
  - _normalize_meta: claves canónicas, alias histórico ("shares"), precedencia
    de lo canónico sobre el alias, y que NO se aliasan claves SoP (net_debt_industrial_m).
  - _engine_fair_values: revenue_base_m y shares_override cambian el cálculo como
    se espera, y un shares_override explícito MANDA sobre la heurística de acciones
    duales (decisión deliberada > detección automática).

Regresión de los residuos cerrados: WOSG_L (−10% por revenue base) y CPAY (+4% por shares).
"""
import json

import pytest

from tools import finalize_thesis as ft


# --------------------------------------------------------------------------- #
# _normalize_meta (puro)
# --------------------------------------------------------------------------- #

def test_normalize_meta_vacio_o_none():
    for m in (None, {}):
        out = ft._normalize_meta(m)
        assert out == {"net_debt_override_m": None, "shares_override": None,
                       "revenue_base_m": None, "fv_adjustment": None}


def test_normalize_meta_claves_canonicas():
    out = ft._normalize_meta({
        "net_debt_override_m": 57.0,
        "shares_override": 231412113,
        "revenue_base_m": 1828.0,
        "note": "se ignora",
    })
    assert out["net_debt_override_m"] == 57.0
    assert out["shares_override"] == 231412113
    assert out["revenue_base_m"] == 1828.0


def test_normalize_meta_alias_shares():
    """El alias histórico "shares" mapea a shares_override (WOSG_L, DE antiguos)."""
    out = ft._normalize_meta({"shares": 270445437})
    assert out["shares_override"] == 270445437


def test_normalize_meta_canonico_gana_al_alias():
    """Si están la clave canónica y el alias, manda la canónica."""
    out = ft._normalize_meta({"shares_override": 100, "shares": 999})
    assert out["shares_override"] == 100


def test_normalize_meta_no_aliasa_claves_sop():
    """net_debt_industrial_m es SoP-específico (DE) y NO se aliasa a net_debt_override_m:
    DE se valora por Sum-of-Parts, fuera de este DCF. Documenta la decisión deliberada."""
    out = ft._normalize_meta({"net_debt_industrial_m": 103.0, "shares": 270445437})
    assert out["net_debt_override_m"] is None
    assert out["shares_override"] == 270445437


# --------------------------------------------------------------------------- #
# _engine_fair_values respeta los overrides (integración con valuation.json)
# --------------------------------------------------------------------------- #

def _sc():
    return {
        "revenue_growth_y1": 0.05, "revenue_growth_y2": 0.05, "revenue_growth_y3": 0.05,
        "revenue_growth_y4": 0.05, "revenue_growth_y5": 0.05,
        "gross_margin": 0.40, "sga_pct": 0.15, "rd_pct": 0.05,
        "da_pct": 0.05, "capex_pct": 0.05, "tax_rate": 0.25,
        "wacc": 0.10, "terminal_multiple": 10.0,
    }


def _scenarios():
    return {"bear": _sc(), "base": _sc(), "bull": _sc()}


def _write_valuation(tmp_path, folder="X", *, revenue=1000e6, shares=100e6, price=10.0,
                     market_cap=None, total_debt=0, cash=0):
    """Escribe un valuation.json mínimo no-financiero. net_debt = total_debt − cash;
    con 0/0 el equity es proporcional al revenue (DCF lineal en la base)."""
    if market_cap is None:
        market_cap = price * shares  # ratio sano (~1.0)
    val = {
        "sector": "Technology", "industry": "Software",
        "current_price": price, "market_cap": market_cap, "shares_outstanding": shares,
        "latest_financials": {"revenue": revenue, "total_debt": total_debt, "cash": cash},
    }
    (tmp_path / f"{folder}_valuation.json").write_text(json.dumps(val), encoding="utf-8")
    return folder


def test_revenue_base_override_escala_el_fair_value(tmp_path):
    """Con net_debt 0, el fair value es lineal en la base de revenue: doblar
    revenue_base_m dobla el fair value (el bug de WOSG_L, al revés)."""
    folder = _write_valuation(tmp_path, revenue=1000e6)
    base, _ = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    doble, _ = ft._engine_fair_values(_scenarios(), tmp_path, folder, {"revenue_base_m": 2000.0})
    assert base and doble
    assert doble["base"] == pytest.approx(2 * base["base"], rel=1e-6)


def test_shares_override_escala_inverso_el_fair_value(tmp_path):
    """fair value/acción ∝ 1/acciones: la mitad de acciones dobla el fair value."""
    folder = _write_valuation(tmp_path, shares=100e6)
    base, _ = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    mitad, _ = ft._engine_fair_values(_scenarios(), tmp_path, folder, {"shares_override": 50e6})
    assert base and mitad
    assert mitad["base"] == pytest.approx(2 * base["base"], rel=1e-6)


def test_shares_override_manda_sobre_heuristica_dual(tmp_path):
    """Con ratio > 1.5 (parece estructura dual) la heurística usaría market_cap/precio
    = 3× las acciones. Un shares_override explícito debe MANDAR sobre esa heurística."""
    # market_cap = 3 × precio × acciones -> ratio 3.0; heurística -> 300M acciones.
    folder = _write_valuation(tmp_path, shares=100e6, price=10.0, market_cap=3e9)
    sin_override, _ = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)       # usa 300M
    con_override, _ = ft._engine_fair_values(_scenarios(), tmp_path, folder, {"shares_override": 100e6})
    assert sin_override and con_override
    # 100M (override) vs 300M (heurística) -> el override da 3× el fair value/acción.
    assert con_override["base"] == pytest.approx(3 * sin_override["base"], rel=1e-6)


def test_net_debt_override_sube_el_equity(tmp_path):
    """Menos deuda neta -> más equity -> mayor fair value. El override (en millones)
    debe leerse vía el normalizador, igual que en el Excel."""
    folder = _write_valuation(tmp_path, total_debt=500e6, cash=0)   # net_debt base = 500M
    base, _ = ft._engine_fair_values(_scenarios(), tmp_path, folder, None)
    sin_deuda, _ = ft._engine_fair_values(_scenarios(), tmp_path, folder, {"net_debt_override_m": 0.0})
    assert base and sin_deuda
    assert sin_deuda["base"] > base["base"]


# --------------------------------------------------------------------------- #
# fv_adjustment: ajuste deliberado sobre el OUTPUT del motor (#3 roadmap)
# --------------------------------------------------------------------------- #

def test_parse_fv_adjustment_valido():
    out = ft._parse_fv_adjustment({"pct": 0.10, "reason": "opcionalidad"})
    assert out == {"pct": 0.10, "reason": "opcionalidad"}


def test_parse_fv_adjustment_sin_reason_pone_default():
    out = ft._parse_fv_adjustment({"pct": -0.05})
    assert out["pct"] == -0.05
    assert out["reason"]  # hay una razón por defecto, no vacía


@pytest.mark.parametrize("raw", [
    None, {}, {"reason": "sin pct"}, {"pct": "0.1"}, {"pct": True}, {"pct": None}, "0.1",
])
def test_parse_fv_adjustment_malformado_es_none(raw):
    """Mal formado o ausente -> None (se ignora sin romper). Bool y string NO cuelan."""
    assert ft._parse_fv_adjustment(raw) is None


def test_normalize_meta_incluye_fv_adjustment():
    out = ft._normalize_meta({"fv_adjustment": {"pct": 0.10, "reason": "x"}})
    assert out["fv_adjustment"] == {"pct": 0.10, "reason": "x"}
    assert ft._normalize_meta({})["fv_adjustment"] is None


# --------------------------------------------------------------------------- #
# _compare_engine: comparación tesis vs motor (ajustado), pura
# --------------------------------------------------------------------------- #

_ENGINE = {"bear": 100.0, "base": 200.0, "bull": 300.0}


def test_compare_engine_sin_datos_es_none():
    assert ft._compare_engine({"bear": 1, "base": 2, "bull": 3}, None, None) is None
    assert ft._compare_engine({}, _ENGINE, None) is None  # sin fair values de la tesis


def test_compare_engine_cuadra_sin_ajuste():
    out = ft._compare_engine(dict(_ENGINE), _ENGINE, None)
    assert out["explained"] is True
    assert out["max_diff"] == pytest.approx(0.0, abs=1e-9)
    assert out["adj_pct"] == 0.0
    assert {r["name"] for r in out["rows"]} == {"bear", "base", "bull"}


def test_compare_engine_diverge_sin_ajuste():
    saved = {"bear": 110.0, "base": 220.0, "bull": 330.0}   # tesis 10% por encima del motor
    out = ft._compare_engine(saved, _ENGINE, None)
    assert out["explained"] is False
    assert out["max_diff"] == pytest.approx(100 * 10 / 110, rel=1e-6)  # (100-110)/110


def test_compare_engine_ajuste_explica_la_divergencia():
    """La tesis está +10% sobre el motor y declara fv_adjustment +10%: cuadra."""
    saved = {"bear": 110.0, "base": 220.0, "bull": 330.0}
    out = ft._compare_engine(saved, _ENGINE, {"pct": 0.10, "reason": "opcionalidad"})
    assert out["explained"] is True
    assert out["adj_pct"] == 0.10
    base_row = next(r for r in out["rows"] if r["name"] == "base")
    assert base_row["target"] == pytest.approx(220.0)        # motor 200 * 1.10
    assert base_row["diff_pct"] == pytest.approx(0.0, abs=1e-9)


def test_compare_engine_ajuste_insuficiente_sigue_divergiendo():
    """Declara +10% pero la tesis está +30%: sigue sin cuadrar (no se 'explica' todo)."""
    saved = {"bear": 130.0, "base": 260.0, "bull": 390.0}
    out = ft._compare_engine(saved, _ENGINE, {"pct": 0.10, "reason": "x"})
    assert out["explained"] is False
