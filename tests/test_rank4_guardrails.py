"""
Tests de los guardarraíles de valoración (rango 4 de la auditoría):
- validate_fair_values: orden bear<=base<=bull y positividad antes de persistir.
- _check_consensus_gap: divergencia simétrica (también vigila el lado alcista).
"""
from tools.finalize_thesis import validate_fair_values
from tools.thesis_reviewer import _check_consensus_gap


# --- validate_fair_values ---

def test_fair_values_validos():
    assert validate_fair_values(10, 20, 30) is None


def test_fair_values_iguales_validos():
    """Empate no es error (bear == base == bull)."""
    assert validate_fair_values(20, 20, 20) is None


def test_orden_invertido_es_error():
    err = validate_fair_values(30, 20, 10)
    assert err and "bear <= base <= bull" in err


def test_base_fuera_de_orden_es_error():
    assert validate_fair_values(10, 35, 30) is not None


def test_negativo_es_error():
    err = validate_fair_values(-5, 20, 30)
    assert err and "positivos" in err


def test_cero_o_faltante_es_error():
    assert validate_fair_values(0, 20, 30) is not None


# --- _check_consensus_gap (lado alcista) ---

_THESIS = """
### Valoración DCF
| Escenario | Precio |
|-----------|--------|
| **Bear** | **$185.00** |
| **Base** | **$235.00** |
| **Bull** | **$295.00** |
"""
# ponderado 40/40/20 = 227


def _levels(thesis, mean):
    issues = _check_consensus_gap(thesis, {"analyst_targets": {"mean": mean}})
    return {i["check"]: i["level"] for i in issues}


def test_alcista_extremo_critical():
    """Ponderado 227 vs consenso 50 -> ratio 4.5 -> critical."""
    lv = _levels(_THESIS, 50)
    assert lv.get("gap_consenso_alcista_extremo") == "critical"


def test_alcista_moderado_warning():
    """Ponderado 227 vs consenso 80 -> ratio 2.8 -> warning."""
    lv = _levels(_THESIS, 80)
    assert lv.get("gap_consenso_alcista") == "warning"


def test_en_linea_con_consenso_sin_alerta():
    """Ponderado 227 vs consenso 227 -> ratio 1.0 -> ninguna alerta de gap."""
    lv = _levels(_THESIS, 227)
    assert not lv


def test_sum_of_parts_degrada_a_warning():
    """Una tesis SoP que diverge al alza es warning, no critical."""
    sop_thesis = _THESIS + "\nValoración por suma de partes (SoP).\n"
    lv = _levels(sop_thesis, 50)
    assert lv.get("gap_consenso_alcista_extremo") == "warning"


def test_lado_bajo_sigue_funcionando():
    """No se rompió el check original a la baja: ponderado 227 vs consenso 2000."""
    lv = _levels(_THESIS, 2000)  # ratio 0.11 -> critical
    assert lv.get("gap_consenso_extremo") == "critical"
