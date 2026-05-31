"""
Motor de valoración determinista (DCF por exit-multiple sobre EBITDA).

FUENTE ÚNICA DE VERDAD del cálculo del valor intrínseco. El analista (Claude/Opus)
decide los SUPUESTOS — crecimiento, márgenes, WACC, múltiplo terminal — y este
módulo hace TODA la aritmética. Ni el LLM ni el Excel deben recalcular el fair
value por su cuenta: esa duplicación era la causa de las divergencias históricas.

Metodología (idéntica a la skill thesis-writer y al modelo Excel):

    Para cada año t de proyección (revenue_0 = revenue_base):
        revenue_t = revenue_{t-1} × (1 + growth_t)
        EBIT_t    = revenue_t × (gross_margin − sga_pct − rd_pct)
        D&A_t     = revenue_t × da_pct
        EBITDA_t  = EBIT_t + D&A_t
        CapEx_t   = revenue_t × capex_pct
        UFCF_t    = EBIT_t × (1 − tax_rate) + D&A_t − CapEx_t

    Terminal Value = EBITDA_n × terminal_multiple      (exit multiple, sobre EBITDA)
    EV             = Σ UFCF_t/(1+WACC)^t + TV/(1+WACC)^n
    Equity Value   = EV − net_debt
    Fair Value/acc = Equity Value / shares_outstanding

Puntos críticos protegidos por tests (bugs históricos):
  - EBIT ≠ EBITDA. EBITDA = EBIT + D&A.
  - UFCF = EBIT×(1−T) + D&A − CapEx (NO se resta D&A dos veces).
  - Terminal Value se calcula sobre EBITDA, nunca sobre EBIT.

NOTA: el cambio en working capital se asume 0 en proyección (igual que el modelo
Excel actual). Modelarlo de forma explícita queda como mejora futura.
"""

from __future__ import annotations

from dataclasses import dataclass

# Ponderación de escenarios (conservador = base > optimista), filosofía value.
WEIGHT_BEAR = 0.40
WEIGHT_BASE = 0.40
WEIGHT_BULL = 0.20

# Suelo de WACC por prudencia (value investing): nunca descontar por debajo del 10%.
WACC_FLOOR = 0.10


@dataclass
class DCFAssumptions:
    """Supuestos de UN escenario. Los decide el analista; el motor no los inventa."""
    revenue_base: float           # Revenue del último año real (año 0), en valor absoluto
    revenue_growth: list[float]   # Crecimiento por año proyectado, p.ej. [0.08, 0.07, 0.06, 0.05, 0.04]
    gross_margin: float           # Margen bruto (fracción: 0.45 = 45%)
    sga_pct: float                # SG&A como fracción de revenue
    rd_pct: float                 # I+D como fracción de revenue
    da_pct: float                 # Depreciación y amortización como fracción de revenue
    capex_pct: float              # CapEx como fracción de revenue
    tax_rate: float               # Tipo impositivo efectivo (sobre EBIT)
    wacc: float                   # Tasa de descuento
    terminal_multiple: float      # Múltiplo EV/EBITDA terminal (exit)

    def __post_init__(self) -> None:
        if self.revenue_base <= 0:
            raise ValueError(f"revenue_base debe ser > 0 (recibido: {self.revenue_base})")
        if not self.revenue_growth:
            raise ValueError("revenue_growth no puede estar vacío")
        if self.wacc <= 0:
            raise ValueError(f"wacc debe ser > 0 (recibido: {self.wacc})")
        if self.terminal_multiple <= 0:
            raise ValueError(f"terminal_multiple debe ser > 0 (recibido: {self.terminal_multiple})")


@dataclass
class YearProjection:
    """Un año de proyección, con todos los intermedios para poder auditar el cálculo."""
    year: int
    revenue: float
    ebit: float
    da: float
    ebitda: float
    capex: float
    ufcf: float
    discount_factor: float
    pv_ufcf: float


@dataclass
class DCFResult:
    """Resultado completo de un escenario. Todo auditable, una sola fuente de verdad."""
    scenario: str
    years: list[YearProjection]
    pv_ufcf_sum: float
    terminal_value: float
    pv_terminal_value: float
    tv_weight_pct: float          # % del EV que procede del Terminal Value (sanity check)
    enterprise_value: float
    net_debt: float
    equity_value: float
    shares_outstanding: float
    fair_value_per_share: float


def run_dcf(
    assumptions: DCFAssumptions,
    net_debt: float,
    shares_outstanding: float,
    scenario_name: str = "base",
) -> DCFResult:
    """
    Ejecuta UN escenario de DCF y devuelve el resultado completo y auditable.

    Args:
        assumptions: supuestos del escenario.
        net_debt: deuda neta (deuda total − caja), en la misma unidad que revenue_base.
        shares_outstanding: acciones en circulación (> 0).
        scenario_name: etiqueta ("bear" / "base" / "bull").

    Returns:
        DCFResult con la proyección año a año, EV, equity y fair value por acción.
    """
    if shares_outstanding <= 0:
        raise ValueError(f"shares_outstanding debe ser > 0 (recibido: {shares_outstanding})")

    a = assumptions
    ebit_margin = a.gross_margin - a.sga_pct - a.rd_pct  # margen operativo implícito

    years: list[YearProjection] = []
    revenue = a.revenue_base
    pv_ufcf_sum = 0.0
    last_ebitda = 0.0

    for i, growth in enumerate(a.revenue_growth, start=1):
        revenue = revenue * (1 + growth)
        ebit = revenue * ebit_margin
        da = revenue * a.da_pct
        ebitda = ebit + da                       # EBITDA = EBIT + D&A (nunca EBIT solo)
        capex = revenue * a.capex_pct
        ufcf = ebit * (1 - a.tax_rate) + da - capex   # NO se resta D&A dos veces
        discount_factor = 1 / (1 + a.wacc) ** i
        pv_ufcf = ufcf * discount_factor

        pv_ufcf_sum += pv_ufcf
        last_ebitda = ebitda
        years.append(YearProjection(
            year=i, revenue=revenue, ebit=ebit, da=da, ebitda=ebitda,
            capex=capex, ufcf=ufcf, discount_factor=discount_factor, pv_ufcf=pv_ufcf,
        ))

    n = len(a.revenue_growth)
    terminal_value = last_ebitda * a.terminal_multiple        # exit multiple SOBRE EBITDA
    pv_terminal_value = terminal_value / (1 + a.wacc) ** n
    enterprise_value = pv_ufcf_sum + pv_terminal_value
    equity_value = enterprise_value - net_debt
    fair_value_per_share = equity_value / shares_outstanding
    tv_weight_pct = (pv_terminal_value / enterprise_value * 100) if enterprise_value else 0.0

    return DCFResult(
        scenario=scenario_name,
        years=years,
        pv_ufcf_sum=pv_ufcf_sum,
        terminal_value=terminal_value,
        pv_terminal_value=pv_terminal_value,
        tv_weight_pct=tv_weight_pct,
        enterprise_value=enterprise_value,
        net_debt=net_debt,
        equity_value=equity_value,
        shares_outstanding=shares_outstanding,
        fair_value_per_share=fair_value_per_share,
    )


def run_three_scenarios(
    bear: DCFAssumptions,
    base: DCFAssumptions,
    bull: DCFAssumptions,
    net_debt: float,
    shares_outstanding: float,
) -> dict:
    """
    Ejecuta los 3 escenarios y devuelve el fair value ponderado (40/40/20).

    Returns:
        dict con los 3 DCFResult y el fair value ponderado por acción.
    """
    results = {
        "bear": run_dcf(bear, net_debt, shares_outstanding, "bear"),
        "base": run_dcf(base, net_debt, shares_outstanding, "base"),
        "bull": run_dcf(bull, net_debt, shares_outstanding, "bull"),
    }
    weighted_fair_value = (
        WEIGHT_BEAR * results["bear"].fair_value_per_share
        + WEIGHT_BASE * results["base"].fair_value_per_share
        + WEIGHT_BULL * results["bull"].fair_value_per_share
    )
    return {
        "scenarios": results,
        "weighted_fair_value": weighted_fair_value,
        "weights": {"bear": WEIGHT_BEAR, "base": WEIGHT_BASE, "bull": WEIGHT_BULL},
    }


def calculate_wacc_capm(
    beta: float,
    risk_free_rate: float,
    equity_risk_premium: float,
    floor: float = WACC_FLOOR,
) -> float:
    """
    Coste de capital vía CAPM con suelo de prudencia.

        Re = risk_free + beta × equity_risk_premium

    Se aplica un suelo (por defecto 10%) por la filosofía value: no descontar
    flujos a tasas demasiado bajas aunque la beta sea reducida.
    """
    cost_of_equity = risk_free_rate + beta * equity_risk_premium
    return max(cost_of_equity, floor)
