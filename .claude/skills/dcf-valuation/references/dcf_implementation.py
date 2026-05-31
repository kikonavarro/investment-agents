# dcf_implementation.py — Implementación completa de DCF para value investing
# Copiar este archivo como tools/dcf_calculator.py en el proyecto

"""
DCF Calculator — Value Investing Style

Principios:
1. Python calcula todo. Claude solo interpreta.
2. Conservador por defecto.
3. Siempre 3 escenarios.
4. Sanity checks obligatorios.
"""

import statistics
import math
from dataclasses import dataclass
from typing import Optional


# ═══════════════════════════════════════════════════
# CONFIGURACIÓN POR DEFECTO
# ═══════════════════════════════════════════════════

@dataclass
class DCFConfig:
    """Parámetros configurables del DCF."""
    projection_years: int = 10
    stage1_years: int = 5           # Años a growth constante
    stage2_years: int = 5           # Años de decay hacia terminal
    
    min_discount_rate: float = 0.10  # Mínimo 10% WACC
    default_discount_rate: float = 0.10
    risk_free_rate: float = 0.04     # ~Bono US 10Y
    market_premium: float = 0.055    # Prima de riesgo histórica
    
    terminal_growth_default: float = 0.025
    terminal_growth_conservative: float = 0.02
    terminal_growth_max: float = 0.035  # NUNCA más de esto
    
    max_growth_large_cap: float = 0.08   # >50B market cap
    max_growth_mid_cap: float = 0.12     # 5-50B
    max_growth_small_cap: float = 0.15   # <5B
    
    maintenance_capex_ratio: float = 0.70  # 70% del capex total
    
    # Pesos de escenarios (conservador > base > optimista)
    weight_conservative: float = 0.40
    weight_base: float = 0.40
    weight_optimistic: float = 0.20
    
    # Margen de seguridad
    min_margin_of_safety: float = 0.25  # 25%
    
    # Alertas
    max_tv_weight: float = 0.75  # Terminal value máximo aceptable
    max_implied_pe: float = 30
    min_implied_pe: float = 5


DEFAULT_CONFIG = DCFConfig()


# ═══════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════

def calculate_cagr(values: list[float], years: Optional[int] = None) -> float:
    """
    Tasa de crecimiento anual compuesta.
    values: lista de valores del más antiguo al más reciente.
    """
    if not values or len(values) < 2:
        return 0.0
    
    start = values[0]
    end = values[-1]
    n = years if years else len(values) - 1
    
    if start <= 0 or end <= 0 or n <= 0:
        return 0.0
    
    return (end / start) ** (1 / n) - 1


def format_number(value: float, currency: str = "$") -> str:
    """Formatea números grandes de forma legible."""
    if abs(value) >= 1e12:
        return f"{currency}{value/1e12:.2f}T"
    elif abs(value) >= 1e9:
        return f"{currency}{value/1e9:.2f}B"
    elif abs(value) >= 1e6:
        return f"{currency}{value/1e6:.2f}M"
    else:
        return f"{currency}{value:,.0f}"


# ═══════════════════════════════════════════════════
# PASO 1: EXTRACCIÓN DE DATOS (yfinance)
# ═══════════════════════════════════════════════════

def extract_financials(ticker_symbol: str) -> dict:
    """
    Extrae todos los datos necesarios de yfinance.
    Devuelve un dict limpio y validado.
    """
    import yfinance as yf
    import pandas as pd
    
    tk = yf.Ticker(ticker_symbol)
    info = tk.info
    income = tk.financials
    balance = tk.balance_sheet
    cashflow = tk.cashflow
    
    def safe_get(df, field, alternatives=None, default=0):
        """Extracción segura de un campo."""
        if df is None or df.empty:
            return default
        names = [field] + (alternatives or [])
        for name in names:
            if name in df.index:
                val = df.loc[name].iloc[0]
                if pd.notna(val):
                    return float(val)
        return default
    
    def safe_history(df, field, alternatives=None, years=10):
        """Extrae historial de un campo."""
        if df is None or df.empty:
            return []
        names = [field] + (alternatives or [])
        for name in names:
            if name in df.index:
                row = df.loc[name]
                vals = [float(v) for v in row.values[:years] if pd.notna(v)]
                return list(reversed(vals))
        return []
    
    # --- Revenue ---
    revenue = safe_get(income, "Total Revenue", ["Revenue"])
    revenue_history = safe_history(income, "Total Revenue", ["Revenue"])
    
    # --- Earnings ---
    net_income = safe_get(income, "Net Income")
    ebit = safe_get(income, "EBIT", ["Operating Income"])
    
    # --- Cash Flow ---
    ocf = safe_get(cashflow, "Operating Cash Flow",
                   ["Total Cash From Operating Activities"])
    capex = abs(safe_get(cashflow, "Capital Expenditure",
                         ["Capital Expenditures"]))
    da = safe_get(cashflow, "Depreciation And Amortization",
                  ["Depreciation & Amortization"])
    
    # FCF history
    ocf_hist = safe_history(cashflow, "Operating Cash Flow",
                            ["Total Cash From Operating Activities"])
    capex_hist = safe_history(cashflow, "Capital Expenditure",
                              ["Capital Expenditures"])
    fcf_history = []
    for i in range(min(len(ocf_hist), len(capex_hist))):
        fcf_history.append(ocf_hist[i] - abs(capex_hist[i]))
    
    # --- Balance Sheet ---
    total_debt = safe_get(balance, "Total Debt",
                          ["Long Term Debt And Capital Lease Obligation",
                           "Long Term Debt"])
    cash = safe_get(balance, "Cash And Cash Equivalents",
                    ["Cash Cash Equivalents And Short Term Investments",
                     "Cash Financial", "Cash"])
    equity = safe_get(balance, "Stockholders Equity",
                      ["Total Equity Gross Minority Interest",
                       "Common Stock Equity"])
    shares = safe_get(balance, "Ordinary Shares Number",
                      ["Share Issued"])
    
    # Si shares no está en balance, buscar en info
    if shares == 0:
        shares = info.get("sharesOutstanding", info.get("impliedSharesOutstanding", 0))
    
    # --- Info del mercado ---
    current_price = info.get("currentPrice",
                    info.get("regularMarketPrice",
                    info.get("previousClose", 0)))
    market_cap = info.get("marketCap", current_price * shares if shares > 0 else 0)
    beta = info.get("beta", 1.0)
    sector = info.get("sector", "Unknown")
    industry = info.get("industry", "Unknown")
    name = info.get("longName", info.get("shortName", ticker_symbol))
    currency = info.get("financialCurrency", info.get("currency", "USD"))
    
    # --- Ratios calculados ---
    fcf = ocf - capex
    interest_expense = safe_get(income, "Interest Expense",
                                ["Interest Expense Non Operating"])
    
    gross_margin = 0
    gross_profit = safe_get(income, "Gross Profit")
    if revenue > 0 and gross_profit > 0:
        gross_margin = gross_profit / revenue
    
    operating_margin = ebit / revenue if revenue > 0 else 0
    net_margin = net_income / revenue if revenue > 0 else 0
    fcf_margin = fcf / revenue if revenue > 0 else 0
    
    roic = 0
    invested_capital = equity + total_debt - cash
    if invested_capital > 0:
        nopat = ebit * (1 - 0.25)  # Asumimos 25% tax si no tenemos dato
        roic = nopat / invested_capital
    
    roe = net_income / equity if equity > 0 else 0
    debt_to_equity = total_debt / equity if equity > 0 else 999
    
    pe = current_price / (net_income / shares) if net_income > 0 and shares > 0 else 999
    pb = current_price / (equity / shares) if equity > 0 and shares > 0 else 999
    fcf_yield = fcf / market_cap if market_cap > 0 else 0
    
    return {
        "ticker": ticker_symbol,
        "name": name,
        "sector": sector,
        "industry": industry,
        "currency": currency,
        "current_price": current_price,
        "market_cap": market_cap,
        "shares_outstanding": shares,
        "beta": beta if beta else 1.0,
        
        "revenue": revenue,
        "revenue_history": revenue_history,
        "net_income": net_income,
        "ebit": ebit,
        "da": da,
        "interest_expense": abs(interest_expense),
        
        "ocf": ocf,
        "capex": capex,
        "fcf": fcf,
        "fcf_history": fcf_history,
        
        "total_debt": total_debt,
        "cash": cash,
        "equity": equity,
        "net_debt": total_debt - cash,
        
        "gross_margin": gross_margin,
        "operating_margin": operating_margin,
        "net_margin": net_margin,
        "fcf_margin": fcf_margin,
        "roic": roic,
        "roe": roe,
        "debt_to_equity": debt_to_equity,
        "pe": pe,
        "pb": pb,
        "fcf_yield": fcf_yield,
        
        "revenue_cagr_5y": calculate_cagr(revenue_history[-6:]) if len(revenue_history) >= 2 else 0,
        "fcf_cagr_5y": calculate_cagr(fcf_history[-6:]) if len(fcf_history) >= 2 else 0,
    }


# ═══════════════════════════════════════════════════
# PASO 2: NORMALIZACIÓN DEL FCF
# ═══════════════════════════════════════════════════

def normalize_fcf(financials: dict, method: str = "auto",
                  config: DCFConfig = DEFAULT_CONFIG) -> tuple[float, str]:
    """
    Normaliza el FCF usando el método más apropiado.
    
    Returns: (fcf_normalizado, método_usado)
    """
    fcf_history = financials.get("fcf_history", [])
    revenue = financials["revenue"]
    net_income = financials["net_income"]
    da = financials["da"]
    capex = financials["capex"]
    
    if method == "auto":
        # Decidir automáticamente
        if len(fcf_history) >= 3:
            # ¿FCF es consistente?
            positive_years = sum(1 for f in fcf_history if f > 0)
            if positive_years >= len(fcf_history) * 0.8:
                # FCF mayormente positivo → mediana
                method = "median"
            else:
                # FCF inconsistente → owner earnings
                method = "owner_earnings"
        else:
            method = "current"  # Pocos datos, usar actual
    
    if method == "median" and len(fcf_history) >= 3:
        normalized = statistics.median(fcf_history[-5:])
        return normalized, f"Mediana FCF últimos {min(5, len(fcf_history))} años"
    
    elif method == "margin" and revenue > 0 and len(fcf_history) >= 3:
        # Calcular margen FCF mediano y aplicar a revenue actual
        revenue_history = financials.get("revenue_history", [])
        if len(revenue_history) >= len(fcf_history):
            margins = []
            for i in range(min(len(fcf_history), len(revenue_history))):
                if revenue_history[i] > 0:
                    margins.append(fcf_history[i] / revenue_history[i])
            if margins:
                median_margin = statistics.median(margins)
                normalized = revenue * median_margin
                return normalized, f"Margen FCF mediano ({median_margin:.1%}) × Revenue actual"
        # Fallback a mediana
        normalized = statistics.median(fcf_history[-5:])
        return normalized, "Mediana FCF (fallback)"
    
    elif method == "owner_earnings":
        maintenance_capex = capex * config.maintenance_capex_ratio
        normalized = net_income + da - maintenance_capex
        return normalized, f"Owner Earnings (maintenance capex = {config.maintenance_capex_ratio:.0%} del total)"
    
    else:  # current
        normalized = financials["fcf"]
        return normalized, "FCF del último año reportado"


# ═══════════════════════════════════════════════════
# PASO 3: ESTIMACIÓN DE CRECIMIENTO
# ═══════════════════════════════════════════════════

def estimate_growth_rates(financials: dict,
                           config: DCFConfig = DEFAULT_CONFIG) -> dict:
    """
    Estima tasas de crecimiento para los 3 escenarios.
    Conservador por defecto. Aplica haircuts por tamaño.
    """
    revenue_cagr = financials.get("revenue_cagr_5y", 0)
    fcf_cagr = financials.get("fcf_cagr_5y", 0)
    market_cap = financials.get("market_cap", 0)
    
    # Tomar el menor crecimiento como base
    # Si fcf_cagr es negativo o muy volátil, usar revenue_cagr
    if fcf_cagr > 0 and revenue_cagr > 0:
        base_growth = min(revenue_cagr, fcf_cagr)
    elif revenue_cagr > 0:
        base_growth = revenue_cagr
    elif fcf_cagr > 0:
        base_growth = fcf_cagr
    else:
        base_growth = 0.02  # Mínimo: inflación
    
    # Haircut por tamaño de empresa
    if market_cap > 50e9:
        max_growth = config.max_growth_large_cap
    elif market_cap > 5e9:
        max_growth = config.max_growth_mid_cap
    else:
        max_growth = config.max_growth_small_cap
    
    base_growth = min(base_growth, max_growth)
    
    # Asegurar que el crecimiento no sea negativo en el base case
    base_growth = max(base_growth, 0.01)
    
    conservative = base_growth * 0.5
    optimistic = min(base_growth * 1.3, max_growth)
    
    return {
        "conservative": round(conservative, 4),
        "base": round(base_growth, 4),
        "optimistic": round(optimistic, 4),
        "revenue_cagr_5y": round(revenue_cagr, 4),
        "fcf_cagr_5y": round(fcf_cagr, 4),
        "max_allowed": max_growth,
    }


def project_growth_schedule(initial_rate: float,
                             terminal_rate: float = 0.025,
                             config: DCFConfig = DEFAULT_CONFIG) -> list[float]:
    """
    Proyecta tasas de crecimiento para cada año.
    Etapa 1 (años 1-5): tasa constante
    Etapa 2 (años 6-10): decay lineal hacia terminal
    """
    rates = []
    total_years = config.stage1_years + config.stage2_years
    
    for year in range(1, total_years + 1):
        if year <= config.stage1_years:
            rates.append(initial_rate)
        else:
            progress = (year - config.stage1_years) / config.stage2_years
            rate = initial_rate + (terminal_rate - initial_rate) * progress
            rates.append(rate)
    
    return rates


# ═══════════════════════════════════════════════════
# PASO 4: TASA DE DESCUENTO
# ═══════════════════════════════════════════════════

def calculate_wacc(financials: dict,
                    config: DCFConfig = DEFAULT_CONFIG) -> float:
    """
    Calcula WACC con suelo mínimo del 10%.
    """
    market_cap = financials["market_cap"]
    total_debt = financials["total_debt"]
    total_value = market_cap + total_debt
    
    if total_value <= 0:
        return config.default_discount_rate
    
    # Cost of Equity (CAPM)
    beta = financials.get("beta", 1.0)
    cost_of_equity = config.risk_free_rate + beta * config.market_premium
    
    # Cost of Debt
    interest = financials.get("interest_expense", 0)
    cost_of_debt = interest / total_debt if total_debt > 0 else 0
    tax_rate = 0.25  # Estimación conservadora
    
    # WACC
    weight_equity = market_cap / total_value
    weight_debt = total_debt / total_value
    
    wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
    
    # Suelo mínimo y techo máximo
    wacc = max(wacc, config.min_discount_rate)
    wacc = min(wacc, 0.15)
    
    return round(wacc, 4)


# ═══════════════════════════════════════════════════
# PASO 5: TERMINAL VALUE
# ═══════════════════════════════════════════════════

def calculate_terminal_value(last_fcf: float, wacc: float,
                              terminal_growth: float = 0.025) -> float:
    """Gordon Growth Model con validación."""
    if terminal_growth >= wacc:
        raise ValueError(
            f"Terminal growth ({terminal_growth:.2%}) >= WACC ({wacc:.2%}). "
            f"Esto produce valor infinito. Reduce terminal growth o aumenta WACC."
        )
    
    return last_fcf * (1 + terminal_growth) / (wacc - terminal_growth)


# ═══════════════════════════════════════════════════
# PASO 6: DCF COMPLETO
# ═══════════════════════════════════════════════════

@dataclass
class DCFResult:
    """Resultado de un escenario de DCF."""
    scenario: str
    normalized_fcf: float
    growth_rate: float
    discount_rate: float
    terminal_growth: float
    projected_fcfs: list
    discounted_fcfs: list
    sum_pv_fcfs: float
    terminal_value: float
    terminal_value_pv: float
    tv_weight_pct: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    shares: float
    intrinsic_value_per_share: float
    fcf_normalization_method: str


def run_dcf_scenario(
    normalized_fcf: float,
    growth_rate: float,
    discount_rate: float,
    terminal_growth: float,
    net_debt: float,
    shares: float,
    scenario_name: str = "base",
    fcf_method: str = "",
    config: DCFConfig = DEFAULT_CONFIG,
) -> DCFResult:
    """Ejecuta un escenario de DCF."""
    
    # Proyectar FCFs
    growth_schedule = project_growth_schedule(growth_rate, terminal_growth, config)
    
    projected_fcfs = []
    current_fcf = normalized_fcf
    for rate in growth_schedule:
        current_fcf = current_fcf * (1 + rate)
        projected_fcfs.append(current_fcf)
    
    # Descontar al presente
    discounted_fcfs = []
    for i, fcf in enumerate(projected_fcfs):
        year = i + 1
        pv = fcf / (1 + discount_rate) ** year
        discounted_fcfs.append(pv)
    
    sum_pv_fcfs = sum(discounted_fcfs)
    
    # Terminal Value
    tv = calculate_terminal_value(projected_fcfs[-1], discount_rate, terminal_growth)
    tv_pv = tv / (1 + discount_rate) ** len(projected_fcfs)
    
    # Enterprise Value → Equity Value → Per Share
    enterprise_value = sum_pv_fcfs + tv_pv
    equity_value = enterprise_value - net_debt
    
    # Protección contra equity value negativo
    if equity_value < 0:
        equity_value = 0
    
    intrinsic_per_share = equity_value / shares if shares > 0 else 0
    tv_weight = tv_pv / enterprise_value * 100 if enterprise_value > 0 else 0
    
    return DCFResult(
        scenario=scenario_name,
        normalized_fcf=normalized_fcf,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        terminal_growth=terminal_growth,
        projected_fcfs=projected_fcfs,
        discounted_fcfs=discounted_fcfs,
        sum_pv_fcfs=sum_pv_fcfs,
        terminal_value=tv,
        terminal_value_pv=tv_pv,
        tv_weight_pct=tv_weight,
        enterprise_value=enterprise_value,
        net_debt=net_debt,
        equity_value=equity_value,
        shares=shares,
        intrinsic_value_per_share=intrinsic_per_share,
        fcf_normalization_method=fcf_method,
    )


# ═══════════════════════════════════════════════════
# PASO 7: TRES ESCENARIOS
# ═══════════════════════════════════════════════════

def run_full_dcf(financials: dict,
                  config: DCFConfig = DEFAULT_CONFIG) -> dict:
    """
    DCF completo con 3 escenarios, sanity checks y señal.
    
    Este es el punto de entrada principal.
    Recibe datos financieros y devuelve la valoración completa.
    """
    # 1. Verificar si DCF es apropiado
    appropriate, reason = is_dcf_appropriate(financials)
    if not appropriate:
        return {
            "error": True,
            "message": f"DCF no recomendado: {reason}",
            "alternative": reason,
        }
    
    # 2. Normalizar FCF
    normalized_fcf, fcf_method = normalize_fcf(financials, config=config)
    
    if normalized_fcf <= 0:
        return {
            "error": True,
            "message": f"FCF normalizado negativo ({format_number(normalized_fcf)}). "
                       f"DCF no produce valoración fiable.",
            "normalized_fcf": normalized_fcf,
            "method": fcf_method,
        }
    
    # 3. Estimar crecimiento
    growth = estimate_growth_rates(financials, config)
    
    # 4. Tasa de descuento
    wacc = calculate_wacc(financials, config)
    
    # 5. Ejecutar 3 escenarios
    net_debt = financials["net_debt"]
    shares = financials["shares_outstanding"]
    
    conservative = run_dcf_scenario(
        normalized_fcf=normalized_fcf,
        growth_rate=growth["conservative"],
        discount_rate=wacc + 0.01,  # +1% extra para conservador
        terminal_growth=config.terminal_growth_conservative,
        net_debt=net_debt,
        shares=shares,
        scenario_name="conservative",
        fcf_method=fcf_method,
        config=config,
    )
    
    base = run_dcf_scenario(
        normalized_fcf=normalized_fcf,
        growth_rate=growth["base"],
        discount_rate=wacc,
        terminal_growth=config.terminal_growth_default,
        net_debt=net_debt,
        shares=shares,
        scenario_name="base",
        fcf_method=fcf_method,
        config=config,
    )
    
    optimistic = run_dcf_scenario(
        normalized_fcf=normalized_fcf,
        growth_rate=growth["optimistic"],
        discount_rate=wacc,
        terminal_growth=config.terminal_growth_default,
        net_debt=net_debt,
        shares=shares,
        scenario_name="optimistic",
        fcf_method=fcf_method,
        config=config,
    )
    
    # 6. Precio ponderado
    weighted_price = (
        conservative.intrinsic_value_per_share * config.weight_conservative +
        base.intrinsic_value_per_share * config.weight_base +
        optimistic.intrinsic_value_per_share * config.weight_optimistic
    )
    
    current_price = financials["current_price"]
    margin_of_safety = (weighted_price - current_price) / weighted_price * 100 \
                       if weighted_price > 0 else -100
    
    # 7. Señal
    signal = classify_signal(margin_of_safety)
    
    # 8. Sanity checks
    warnings = run_sanity_checks(
        base_result=base,
        financials=financials,
        config=config,
    )
    
    # 9. Sensitivity analysis
    sensitivity = run_sensitivity(
        normalized_fcf=normalized_fcf,
        base_growth=growth["base"],
        base_wacc=wacc,
        net_debt=net_debt,
        shares=shares,
        config=config,
    )
    
    return {
        "error": False,
        "ticker": financials["ticker"],
        "name": financials["name"],
        "currency": financials["currency"],
        "current_price": current_price,
        "date": __import__("datetime").date.today().isoformat(),
        
        "normalized_fcf": normalized_fcf,
        "fcf_method": fcf_method,
        "wacc": wacc,
        "growth_rates": growth,
        
        "scenarios": {
            "conservative": conservative,
            "base": base,
            "optimistic": optimistic,
        },
        
        "weighted_target_price": round(weighted_price, 2),
        "margin_of_safety_pct": round(margin_of_safety, 2),
        "signal": signal,
        "warnings": warnings,
        "sensitivity": sensitivity,
    }


# ═══════════════════════════════════════════════════
# PASO 8: ANÁLISIS DE SENSIBILIDAD
# ═══════════════════════════════════════════════════

def run_sensitivity(
    normalized_fcf: float,
    base_growth: float,
    base_wacc: float,
    net_debt: float,
    shares: float,
    config: DCFConfig = DEFAULT_CONFIG,
) -> dict:
    """
    Matriz de sensibilidad Growth × WACC.
    5×5 tabla con el caso base en el centro.
    """
    growth_deltas = [-0.02, -0.01, 0, 0.01, 0.02]
    wacc_deltas = [-0.02, -0.01, 0, 0.01, 0.02]
    
    growth_labels = [f"{(base_growth + d)*100:.1f}%" for d in growth_deltas]
    wacc_labels = [f"{(base_wacc + d)*100:.1f}%" for d in wacc_deltas]
    
    table = []
    for g_delta in growth_deltas:
        row = []
        growth = max(base_growth + g_delta, 0)
        for w_delta in wacc_deltas:
            wacc = max(base_wacc + w_delta, 0.05)
            try:
                schedule = project_growth_schedule(growth, config.terminal_growth_default, config)
                
                current_fcf = normalized_fcf
                projected = []
                for rate in schedule:
                    current_fcf *= (1 + rate)
                    projected.append(current_fcf)
                
                pv_sum = sum(
                    fcf / (1 + wacc) ** (i+1)
                    for i, fcf in enumerate(projected)
                )
                
                tv = calculate_terminal_value(
                    projected[-1], wacc, config.terminal_growth_default
                )
                tv_pv = tv / (1 + wacc) ** len(projected)
                
                ev = pv_sum + tv_pv
                eq = max(ev - net_debt, 0)
                price = eq / shares if shares > 0 else 0
                row.append(round(price, 2))
            except (ValueError, ZeroDivisionError):
                row.append(None)
        table.append(row)
    
    return {
        "growth_labels": growth_labels,
        "wacc_labels": wacc_labels,
        "table": table,
    }


# ═══════════════════════════════════════════════════
# PASO 9: SANITY CHECKS
# ═══════════════════════════════════════════════════

def is_dcf_appropriate(financials: dict) -> tuple[bool, str]:
    """¿Es DCF el método correcto para esta empresa?"""
    sector = financials.get("sector", "").lower()
    industry = financials.get("industry", "").lower()
    
    if any(x in sector for x in ["financial", "bank"]):
        return False, "Sector financiero. Usar P/Book Value o Dividend Discount Model."
    
    if any(x in industry for x in ["reit", "real estate investment"]):
        return False, "REIT. Usar P/FFO o P/AFFO en lugar de DCF."
    
    if any(x in industry for x in ["insurance"]):
        return False, "Aseguradora. Usar P/Book o P/Embedded Value."
    
    fcf_history = financials.get("fcf_history", [])
    if len(fcf_history) >= 3 and all(f < 0 for f in fcf_history[-3:]):
        return False, "FCF negativo 3+ años consecutivos. DCF no fiable. Considerar valoración por activos."
    
    return True, "DCF es aplicable."


def classify_signal(margin_of_safety: float) -> str:
    """Señal basada en margen de seguridad."""
    if margin_of_safety >= 40:
        return "🟢 MUY INFRAVALORADA — Oportunidad clara con alto margen"
    elif margin_of_safety >= 25:
        return "🟢 INFRAVALORADA — Margen de seguridad aceptable para compra"
    elif margin_of_safety >= 10:
        return "🟡 LIGERAMENTE INFRAVALORADA — Watchlist, esperar mejor precio"
    elif margin_of_safety >= -10:
        return "⚪ VALOR JUSTO — No hay margen de seguridad suficiente"
    elif margin_of_safety >= -25:
        return "🟠 LIGERAMENTE SOBREVALORADA — Evitar compra"
    else:
        return "🔴 SOBREVALORADA — No invertir"


def run_sanity_checks(base_result: DCFResult, financials: dict,
                       config: DCFConfig = DEFAULT_CONFIG) -> list[str]:
    """Checks obligatorios antes de confiar en la valoración."""
    warnings = []
    
    # 1. Terminal Value weight
    if base_result.tv_weight_pct > 85:
        warnings.append(
            f"🔴 Terminal Value = {base_result.tv_weight_pct:.0f}% del valor total. "
            f"Valoración MUY especulativa. No confiar."
        )
    elif base_result.tv_weight_pct > config.max_tv_weight * 100:
        warnings.append(
            f"🟠 Terminal Value = {base_result.tv_weight_pct:.0f}% del valor total. "
            f"Valoración depende mucho del largo plazo."
        )
    else:
        warnings.append(
            f"✅ Terminal Value = {base_result.tv_weight_pct:.0f}% del valor total."
        )
    
    # 2. Implied P/E
    ni = financials.get("net_income", 0)
    if ni > 0:
        implied_pe = base_result.equity_value / ni
        if implied_pe > config.max_implied_pe:
            warnings.append(
                f"🟠 P/E implícito = {implied_pe:.1f}x. ¿Crecimiento demasiado optimista?"
            )
        elif implied_pe < config.min_implied_pe:
            warnings.append(
                f"🟠 P/E implícito = {implied_pe:.1f}x. ¿Hay un riesgo no considerado?"
            )
        else:
            warnings.append(f"✅ P/E implícito = {implied_pe:.1f}x. Razonable.")
    
    # 3. Growth vs histórico
    base_growth = base_result.growth_rate
    historical = financials.get("revenue_cagr_5y", 0)
    if historical > 0 and base_growth > historical * 1.5:
        warnings.append(
            f"🟠 Growth base ({base_growth:.1%}) >> histórico ({historical:.1%}). Justificar."
        )
    
    # 4. Deuda
    de = financials.get("debt_to_equity", 0)
    if de > 2:
        warnings.append(f"🟠 Debt/Equity = {de:.1f}. Empresa muy apalancada.")
    elif de > 1:
        warnings.append(f"🟡 Debt/Equity = {de:.1f}. Deuda moderada-alta.")
    
    # 5. FCF consistency
    fcf_history = financials.get("fcf_history", [])
    if fcf_history:
        negative_years = sum(1 for f in fcf_history if f < 0)
        total_years = len(fcf_history)
        if negative_years >= 2:
            warnings.append(
                f"🟠 FCF negativo en {negative_years}/{total_years} años. Inconsistente."
            )
        else:
            warnings.append(f"✅ FCF positivo en {total_years - negative_years}/{total_years} años.")
    
    # 6. Net debt vs equity value
    if financials["net_debt"] > base_result.equity_value * 0.5:
        warnings.append(
            f"🟡 Deuda neta ({format_number(financials['net_debt'])}) es >50% del equity value."
        )
    
    return warnings


# ═══════════════════════════════════════════════════
# PASO 10: FORMATO PARA PRESENTACIÓN
# ═══════════════════════════════════════════════════

def format_dcf_report(results: dict) -> str:
    """
    Formatea los resultados del DCF en un reporte legible.
    Esto es lo que se puede enviar a Claude para interpretar,
    o mostrar directamente al usuario.
    """
    if results.get("error"):
        return f"⚠️ {results['message']}"
    
    r = results
    cons = r["scenarios"]["conservative"]
    base = r["scenarios"]["base"]
    opti = r["scenarios"]["optimistic"]
    curr = r["currency"]
    
    report = f"""
{'═' * 56}
  DCF VALUATION: {r['name']} ({r['ticker']})
  Fecha: {r['date']} | Moneda: {curr}
{'═' * 56}

  Precio actual: {curr} {r['current_price']:.2f}
  FCF normalizado: {format_number(r['normalized_fcf'], curr)}
  Método: {r['fcf_method']}
  WACC: {r['wacc']:.1%}

  ┌─────────────┬────────────┬────────────┬────────────┐
  │             │ Conserv.   │    Base    │  Optim.    │
  ├─────────────┼────────────┼────────────┼────────────┤
  │ Growth (1-5)│  {cons.growth_rate:>7.1%}   │  {base.growth_rate:>7.1%}  │  {opti.growth_rate:>7.1%}   │
  │ WACC        │  {cons.discount_rate:>7.1%}   │  {base.discount_rate:>7.1%}  │  {opti.discount_rate:>7.1%}   │
  │ Terminal g  │  {cons.terminal_growth:>7.1%}   │  {base.terminal_growth:>7.1%}  │  {opti.terminal_growth:>7.1%}   │
  │ TV Weight   │  {cons.tv_weight_pct:>6.0f}%   │  {base.tv_weight_pct:>6.0f}%  │  {opti.tv_weight_pct:>6.0f}%   │
  │ Target Price│ {curr}{cons.intrinsic_value_per_share:>8.2f}  │ {curr}{base.intrinsic_value_per_share:>8.2f} │ {curr}{opti.intrinsic_value_per_share:>8.2f}  │
  └─────────────┴────────────┴────────────┴────────────┘

  Precio objetivo ponderado: {curr} {r['weighted_target_price']:.2f}
  Margen de seguridad: {r['margin_of_safety_pct']:+.1f}%

  {r['signal']}

  SANITY CHECKS:
"""
    for w in r["warnings"]:
        report += f"  {w}\n"
    
    # Sensitivity table
    sens = r["sensitivity"]
    report += f"\n  SENSIBILIDAD (precio por acción):\n"
    report += f"  {'Growth↓ WACC→':>12}"
    for label in sens["wacc_labels"]:
        report += f" {label:>8}"
    report += "\n"
    
    for i, g_label in enumerate(sens["growth_labels"]):
        report += f"  {g_label:>12}"
        for val in sens["table"][i]:
            if val is not None:
                report += f" {curr}{val:>7.0f}"
            else:
                report += f" {'N/A':>7}"
        report += "\n"
    
    report += f"\n{'═' * 56}\n"
    
    return report


# ═══════════════════════════════════════════════════
# PUNTO DE ENTRADA RÁPIDO
# ═══════════════════════════════════════════════════

def quick_dcf(ticker: str) -> str:
    """
    DCF completo en una sola llamada.
    Descarga datos, calcula, y devuelve reporte formateado.
    
    Ejemplo:
        print(quick_dcf("AAPL"))
        print(quick_dcf("EUFI.PA"))
        print(quick_dcf("SAN.MC"))
    """
    financials = extract_financials(ticker)
    results = run_full_dcf(financials)
    return format_dcf_report(results)


# Si se ejecuta directamente
if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    print(quick_dcf(ticker))
