"""
Tests de la reconciliación de acciones en la fuente (tools/financial_data._reconcile_shares).

Fijan el contrato de la corrección de estructuras duales movida desde la
verificación (finalize_thesis) a la fuente (get_company_data):

  - ratio market_cap/(precio*shares) ~1.0  -> datos sanos, no se toca.
  - ratio > 1.5                            -> estructura dual, shares = market_cap/precio.
  - ratio < 0.02 (peniques UK)             -> NO es problema de acciones; se deja intacto.
  - guardas de cero/negativos              -> no se divide ni se fabrica nada.

Son tests puros: no tocan la red (Yahoo). El helper recibe ya los tres números.
"""

import pytest

from tools.financial_data import _reconcile_shares, _DUAL_CLASS_RATIO


def test_ratio_sano_no_modifica():
    """market_cap == precio * shares (ratio 1.0): no se toca nada."""
    shares = 1_000_000_000
    price = 100.0
    market_cap = price * shares  # ratio exactamente 1.0
    out, info = _reconcile_shares(shares, market_cap, price)
    assert out == shares
    assert info is None


def test_estructura_dual_corrige_a_market_cap_sobre_precio():
    """ratio > 1.5 (PUIG-like): shares de Yahoo es solo 1 clase; se corrige al total."""
    raw_shares = 270_000_000        # solo clase A (cotizada)
    price = 20.0
    market_cap = 11_000_000_000     # capitalización total (clase A + B)
    out, info = _reconcile_shares(raw_shares, market_cap, price)

    assert out == pytest.approx(market_cap / price)   # 550M acciones reales
    assert out == pytest.approx(550_000_000)
    assert info is not None
    assert info["reason"] == "dual_class"
    assert info["raw"] == raw_shares
    assert info["corrected"] == pytest.approx(out)
    assert info["ratio"] == pytest.approx(11e9 / (20.0 * 270e6), abs=1e-3)


def test_peniques_uk_no_se_toca():
    """ratio ~0.01 (precio en GBp, fundamentales en GBP): es escala de PRECIO, no de
    acciones. La rama dual (>1.5) no debe dispararse: las acciones quedan intactas."""
    shares = 100_000_000
    price = 2500.0                  # 2.500 peniques = 25 libras
    market_cap = 2_500_000_000      # capitalización en libras reales
    ratio = market_cap / (price * shares)
    assert ratio < 0.02             # confirma que es el caso peniques
    out, info = _reconcile_shares(shares, market_cap, price)
    assert out == shares
    assert info is None


def test_umbral_justo_por_encima_corrige():
    """Apenas por encima de 1.5 -> se corrige."""
    shares = 1_000_000
    price = 10.0
    # ratio = 1.6 -> market_cap = 1.6 * price * shares
    market_cap = 1.6 * price * shares
    out, info = _reconcile_shares(shares, market_cap, price)
    assert info is not None
    assert out == pytest.approx(market_cap / price)


def test_umbral_exacto_no_corrige():
    """Ratio == 1.5 no es '> 1.5': no se toca (la frontera es estricta)."""
    shares = 1_000_000
    price = 10.0
    market_cap = _DUAL_CLASS_RATIO * price * shares  # ratio exactamente 1.5
    out, info = _reconcile_shares(shares, market_cap, price)
    assert out == shares
    assert info is None


@pytest.mark.parametrize("shares,market_cap,price", [
    (0, 1_000_000_000, 10.0),       # sin acciones
    (1_000_000, 0, 10.0),           # sin market cap
    (1_000_000, 1_000_000_000, 0),  # sin precio
    (-5, 1_000_000_000, 10.0),      # acciones negativas (basura)
])
def test_guardas_de_cero_y_negativos(shares, market_cap, price):
    """Sin los tres números positivos no se puede calcular el ratio: se devuelve tal cual."""
    out, info = _reconcile_shares(shares, market_cap, price)
    assert out == shares
    assert info is None


def test_idempotente_sobre_valor_ya_corregido():
    """Reconciliar un valor ya corregido (ratio ~1.0) no lo vuelve a tocar:
    garantiza que la fuente y la verificación de finalize no se pisan."""
    raw_shares = 270_000_000
    price = 20.0
    market_cap = 11_000_000_000
    corrected, _ = _reconcile_shares(raw_shares, market_cap, price)
    # Segunda pasada con las acciones ya corregidas -> ratio 1.0 -> sin cambios.
    again, info = _reconcile_shares(corrected, market_cap, price)
    assert again == pytest.approx(corrected)
    assert info is None
