"""
Tests del escáner de watchlist (loop cerrado): lógica pura de cruce fair value vs
precio vivo. No tocan la red (la parte con red, fetch_live_prices, se aísla aparte).
"""
import json

import pytest

from tools.signals import classify_signal
from tools import watchlist as wl


# --- signals.classify_signal: bandas value ---

@pytest.mark.parametrize("mos,label", [
    (45, "MUY INFRAVALORADA"),
    (30, "INFRAVALORADA"),
    (15, "LIGERAMENTE INFRAVALORADA"),
    (0, "VALOR JUSTO"),
    (-15, "SOBREVALORADA"),
    (-40, "MUY SOBREVALORADA"),
])
def test_classify_signal_bandas(mos, label):
    _, lab, _ = classify_signal(mos)
    assert lab == label


# --- watchlist.evaluate ---

def _fv(bear=80, base=100, bull=140, weighted=100, saved=90, currency="$"):
    return {"bear": bear, "base": base, "bull": bull, "weighted": weighted,
            "saved_price": saved, "currency": currency, "date": "2026-05-01"}


def test_evaluate_infravalorada_y_suelo():
    """Precio por debajo del bear → MoS alto, BUY, flag de suelo (below_bear)."""
    r = wl.evaluate(_fv(), live_price=70)
    assert r["mos"] == pytest.approx(30.0)        # (100-70)/100
    assert r["action"] == "BUY"
    assert r["below_bear"] is True                # 70 <= bear(80)
    assert r["above_bull"] is False
    assert r["price_change_pct"] == pytest.approx((70 - 90) / 90 * 100)


def test_evaluate_sobrevalorada_y_techo():
    """Precio por encima del bull → MoS muy negativo, SELL, flag de techo (above_bull)."""
    r = wl.evaluate(_fv(), live_price=150)
    assert r["mos"] == pytest.approx(-50.0)       # (100-150)/100
    assert r["action"] == "SELL"
    assert r["above_bull"] is True                # 150 >= bull(140)
    assert r["below_bear"] is False


def test_evaluate_valor_justo_es_hold():
    r = wl.evaluate(_fv(), live_price=100)
    assert r["mos"] == pytest.approx(0.0)
    assert r["action"] == "HOLD"


def test_evaluate_fair_value_no_positivo_es_na():
    """FV ponderado <= 0 (pre-profit/NAV/SoP o datos a revisar) → N/A, no 'VALOR JUSTO'."""
    r = wl.evaluate(_fv(bear=-30, base=-10, bull=20, weighted=-12), live_price=100)
    assert r["action"] == "NA"
    assert r["mos"] == 0.0
    assert "N/A" in r["label"]
    assert r["below_bear"] is False and r["above_bull"] is False


def test_evaluate_sin_saved_price_change_none():
    r = wl.evaluate(_fv(saved=0), live_price=100)
    assert r["price_change_pct"] is None


def test_evaluate_suspect_si_mos_extremo_al_finalizar():
    """FV ya extremo vs el precio DE LA TESIS (caso OXY) → suspect: FV/método a revisar."""
    # saved=63, weighted=228 → mos_origin = (228-63)/228 ≈ +72% ≥ 50 → suspect
    r = wl.evaluate(_fv(bear=171, base=238, bull=321, weighted=228, saved=63), live_price=57)
    assert r["mos_origin"] == pytest.approx((228 - 63) / 228 * 100)
    assert r["suspect"] is True


def test_evaluate_no_suspect_si_oportunidad_por_caida_reciente():
    """FV cerca del precio al finalizar (mos_origin pequeño); la oportunidad nace de una
    caída POSTERIOR → no es sospechosa, es real."""
    # saved=100, weighted=105 → mos_origin ≈ +4.8% < 50 → no suspect, aunque el precio caiga
    r = wl.evaluate(_fv(bear=90, base=105, bull=120, weighted=105, saved=100), live_price=70)
    assert r["suspect"] is False
    assert r["mos"] > 25  # ahora sí en zona de compra (el precio cayó tras la tesis)


# --- watchlist.scan ---

def test_scan_ordena_por_mos_desc_y_omite_sin_precio():
    saved = {
        "UNDER": _fv(weighted=100),   # con precio 70 → +30%
        "OVER": _fv(weighted=100),    # con precio 150 → -50%
        "NOPRICE": _fv(weighted=100),
    }
    prices = {"UNDER": 70, "OVER": 150}  # NOPRICE no tiene precio vivo
    rows = wl.scan(saved, prices)
    assert [r["ticker"] for r in rows] == ["UNDER", "OVER"]   # ordenado por MoS desc
    assert rows[0]["mos"] > rows[1]["mos"]
    assert all(r["ticker"] != "NOPRICE" for r in rows)         # omitido


def test_scan_precio_invalido_se_omite():
    saved = {"A": _fv()}
    assert wl.scan(saved, {"A": 0}) == []
    assert wl.scan(saved, {"A": -5}) == []


# --- watchlist.load_saved_fair_values (con tmp dir) ---

def _write_history(tmp_path, folder, entries):
    d = tmp_path / folder
    d.mkdir()
    (d / "history.json").write_text(json.dumps(entries), encoding="utf-8")


def test_load_saved_fair_values_lee_ultima_entry(tmp_path):
    # AAA: dos entries, debe tomar la última con fair_value_base
    _write_history(tmp_path, "AAA", [
        {"date": "2026-04-01", "current_price": 50, "fair_value_bear": 40,
         "fair_value_base": 60, "fair_value_bull": 80, "fair_value_weighted": 60, "currency": "$"},
        {"date": "2026-05-01", "current_price": 55, "fair_value_bear": 45,
         "fair_value_base": 65, "fair_value_bull": 85, "fair_value_weighted": 65, "currency": "$"},
    ])
    # BBB: sin fair values → se omite
    _write_history(tmp_path, "BBB", [{"date": "2026-05-01", "current_price": 10}])

    out = wl.load_saved_fair_values(valuations_dir=tmp_path)
    assert set(out.keys()) == {"AAA"}
    assert out["AAA"]["weighted"] == 65
    assert out["AAA"]["saved_price"] == 55
    assert out["AAA"]["date"] == "2026-05-01"


def test_load_saved_fair_values_calcula_weighted_si_falta(tmp_path):
    """Si no hay fair_value_weighted guardado, se calcula 40/40/20."""
    _write_history(tmp_path, "CCC", [
        {"date": "2026-05-01", "current_price": 100, "fair_value_bear": 100,
         "fair_value_base": 200, "fair_value_bull": 300, "currency": "$"},
    ])
    out = wl.load_saved_fair_values(valuations_dir=tmp_path)
    assert out["CCC"]["weighted"] == pytest.approx(0.4 * 100 + 0.4 * 200 + 0.2 * 300)  # 180
