"""
Tests del rango 6 de la auditoría:
- _extract_fair_values entiende el formato bullet **Bear ($150):** (no solo tablas).
- _run_review_gate aborta si hay críticos, no bloquea si faltan ficheros o el
  reviewer falla.
"""
import json

import pytest

from tools.thesis_reviewer import _extract_fair_values
from tools import finalize_thesis as ft


# --- Extracción formato bullet ---

BULLET_THESIS = """
### Valoración DCF
**Bear ($150):** capex IA se modera, AMD gana share. Caída -33%.
**Base ($300):** trayectoria continúa, share premium. Upside +33%.
**Bull ($520):** era IA acelera, nuevos TAM. Upside +131%.
"""

RANGE_THESIS = """
**Bear ($15-17):** GLP-1 colapsa. La acción cae 40%+.
**Base ($30-34):** estabiliza el negocio.
**Bull ($50-55):** se convierte en plataforma DTC.
"""


def test_extrae_formato_bullet():
    fv = _extract_fair_values(BULLET_THESIS)
    assert fv == {"bear": 150.0, "base": 300.0, "bull": 520.0}


def test_extrae_bullet_con_rango_toma_extremo_bajo():
    fv = _extract_fair_values(RANGE_THESIS)
    assert fv["bear"] == 15.0
    assert fv["base"] == 30.0
    assert fv["bull"] == 50.0


def test_tabla_sigue_funcionando():
    tabla = (
        "| **Bear** | 11% | 16x | **$185.00** |\n"
        "| **Base** | 10% | 18x | **$235.00** |\n"
        "| **Bull** | 9% | 20x | **$295.00** |\n"
    )
    fv = _extract_fair_values(tabla)
    assert fv == {"bear": 185.0, "base": 235.0, "bull": 295.0}


# --- Review gate ---

_FAIL_THESIS = """
### Valoración DCF
**Bear ($5):** todo va mal.
**Base ($10):** regular.
**Bull ($15):** bien.
"""

_VALUATION = {
    "ticker": "X",
    "current_price": 200.0,
    "shares_outstanding": 1_000_000_000,
    "latest_financials": {"ebitda": 20_000_000_000, "total_debt": 0, "cash": 0},
}


def test_gate_sin_ficheros_no_bloquea(tmp_path):
    """Sin tesis ni datos no hay nada que revisar: no debe abortar."""
    ft._run_review_gate("X", tmp_path, "X")  # no lanza


def test_gate_fail_aborta(tmp_path):
    """Bear ($5) es <20% del precio ($200) -> critical -> el gate aborta."""
    (tmp_path / "X_tesis_inversion.md").write_text(_FAIL_THESIS, encoding="utf-8")
    (tmp_path / "X_valuation.json").write_text(json.dumps(_VALUATION), encoding="utf-8")
    with pytest.raises(SystemExit):
        ft._run_review_gate("X", tmp_path, "X")


def test_gate_reviewer_corrupto_no_bloquea(tmp_path):
    """Si el reviewer falla (JSON corrupto), se avisa y se continúa, no se bloquea."""
    (tmp_path / "X_tesis_inversion.md").write_text("texto", encoding="utf-8")
    (tmp_path / "X_valuation.json").write_text("{ json roto", encoding="utf-8")
    ft._run_review_gate("X", tmp_path, "X")  # no lanza
