"""
Quality Gates — validaciones post-analyst para evitar garbage in/garbage out.
Cada check devuelve una lista de warnings. Si hay warnings críticos,
la confianza baja y los agentes downstream son avisados.
"""


def validate_valuation(valuation: dict) -> dict:
    """
    Ejecuta todas las validaciones sobre el JSON de valoración.

    Returns:
        {
            "confidence": "high" | "medium" | "low",
            "warnings": [{"level": "critical|warning|info", "check": "nombre", "message": "..."}],
            "passed": int,
            "failed": int,
        }
    """
    warnings = []
    warnings.extend(_check_price(valuation))
    warnings.extend(_check_revenue(valuation))
    warnings.extend(_check_margins(valuation))
    warnings.extend(_check_wacc(valuation))
    warnings.extend(_check_terminal_multiple(valuation))
    warnings.extend(_check_historical_depth(valuation))
    warnings.extend(_check_shares(valuation))
    warnings.extend(_check_debt_sanity(valuation))
    warnings.extend(_check_extreme_valuation(valuation))
    warnings.extend(_check_negative_fair_value(valuation))
    warnings.extend(_check_terminal_value_fraction(valuation))
    warnings.extend(_check_revenue_decline_base(valuation))
    warnings.extend(_check_wacc_range_by_market(valuation))

    critical = sum(1 for w in warnings if w["level"] == "critical")
    warning_count = sum(1 for w in warnings if w["level"] == "warning")

    total_checks = 13
    failed = critical + warning_count

    if critical >= 2:
        confidence = "low"
    elif critical >= 1 or warning_count >= 3:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "confidence": confidence,
        "warnings": warnings,
        "passed": total_checks - failed,
        "failed": failed,
    }


def print_quality_report(result: dict):
    """Imprime el reporte de calidad de forma concisa."""
    conf = result["confidence"]
    icon = {"high": "OK", "medium": "!!", "low": "XX"}[conf]
    print(f"\n  [{icon}] Quality Gate: confianza {conf.upper()} "
          f"({result['passed']}/{result['passed'] + result['failed']} checks OK)")

    for w in result["warnings"]:
        level_icon = {"critical": "XX", "warning": "!!", "info": "--"}[w["level"]]
        print(f"    [{level_icon}] {w['check']}: {w['message']}")


# --- Checks individuales ---

def _check_price(v: dict) -> list[dict]:
    price = v.get("current_price", 0)
    if not price or price <= 0:
        return [{"level": "critical", "check": "precio",
                 "message": f"Precio actual inválido: {price}"}]
    return []


def _check_revenue(v: dict) -> list[dict]:
    latest = v.get("latest_financials", {})
    rev = latest.get("revenue", 0)
    if not rev or rev <= 0:
        return [{"level": "critical", "check": "revenue",
                 "message": "Revenue del último año es 0 o negativo"}]
    return []


def _check_margins(v: dict) -> list[dict]:
    latest = v.get("latest_financials", {})
    warnings = []

    gm = latest.get("gross_margin", 0)
    if gm is not None and (gm < 0 or gm > 1.0):
        warnings.append({"level": "warning", "check": "margen_bruto",
                         "message": f"Margen bruto fuera de rango: {gm:.1%}"})

    om = latest.get("operating_margin", 0)
    if om is not None and om < -0.5:
        warnings.append({"level": "warning", "check": "margen_operativo",
                         "message": f"Margen operativo muy negativo: {om:.1%}"})

    return warnings


def _check_wacc(v: dict) -> list[dict]:
    scenarios = v.get("scenarios", {})
    base = scenarios.get("base", {})
    wacc = base.get("wacc", 0)
    if wacc < 0.03 or wacc > 0.25:
        return [{"level": "warning", "check": "wacc",
                 "message": f"WACC fuera de rango razonable (3-25%): {wacc:.1%}"}]
    return []


def _check_terminal_multiple(v: dict) -> list[dict]:
    scenarios = v.get("scenarios", {})
    base = scenarios.get("base", {})
    tv = base.get("terminal_multiple", 0)
    if tv < 3 or tv > 40:
        return [{"level": "warning", "check": "terminal_multiple",
                 "message": f"Múltiplo terminal fuera de rango (3-40x): {tv:.0f}x"}]
    return []


def _check_historical_depth(v: dict) -> list[dict]:
    years = v.get("historical_years", [])
    if len(years) < 2:
        return [{"level": "critical", "check": "historico",
                 "message": f"Solo {len(years)} año(s) de datos. Mínimo recomendado: 3"}]
    if len(years) < 3:
        return [{"level": "warning", "check": "historico",
                 "message": f"Solo {len(years)} años de datos. Recomendado: 3+"}]
    return []


def _check_shares(v: dict) -> list[dict]:
    shares = v.get("shares_outstanding", 0)
    if not shares or shares <= 0:
        return [{"level": "warning", "check": "acciones",
                 "message": "Shares outstanding es 0 o no disponible"}]
    return []


def _check_debt_sanity(v: dict) -> list[dict]:
    latest = v.get("latest_financials", {})
    debt = latest.get("total_debt", 0) or 0
    equity = latest.get("total_equity", 0) or 0
    if equity > 0 and debt / equity > 5:
        return [{"level": "warning", "check": "deuda",
                 "message": f"Ratio deuda/equity muy alto: {debt/equity:.1f}x"}]
    if equity < 0:
        return [{"level": "warning", "check": "patrimonio",
                 "message": "Patrimonio neto negativo"}]
    return []


def _check_extreme_valuation(v: dict) -> list[dict]:
    """Early warning si EV/EBITDA > 50x (valoración extrema)."""
    price = v.get("current_price", 0)
    shares = v.get("shares_outstanding", 0)
    latest = v.get("latest_financials", {})
    debt = latest.get("total_debt", 0) or 0
    cash = latest.get("cash", 0) or 0
    ebitda = latest.get("ebitda", 0) or 0

    if not ebitda or ebitda <= 0 or not price or not shares:
        return []

    market_cap = price * shares
    ev = market_cap + debt - cash
    ev_ebitda = ev / ebitda

    if ev_ebitda > 50:
        return [{"level": "info", "check": "valoracion_extrema",
                 "message": (
                     f"EV/EBITDA = {ev_ebitda:.0f}x (>50x). Valoración extrema. "
                     f"Los escenarios automáticos pueden no ser apropiados. "
                     f"Considerar diseñar escenarios manuales con múltiplos/growth "
                     f"coherentes con el perfil de la empresa."
                 )}]
    return []


def _check_negative_fair_value(v: dict) -> list[dict]:
    """Detecta fair values negativos o cero en algún escenario."""
    scenarios = v.get("scenarios", {})
    warnings = []
    for name, sc in scenarios.items():
        # Calcular fair value implícito si hay datos suficientes
        # Buscar fair_value directo o inferir de EV negativo
        wacc = sc.get("wacc", 0)
        tv = sc.get("terminal_multiple", 0)
        latest = v.get("latest_financials", {})
        debt = latest.get("total_debt", 0) or 0
        cash = latest.get("cash", 0) or 0
        ebitda = latest.get("ebitda", 0) or 0
        shares = v.get("shares_outstanding", 0)

        if not all([ebitda, tv, shares, wacc]):
            continue

        # Estimación rápida: TV = EBITDA * multiple, descontado 5 años
        implied_ev = (ebitda * tv) / ((1 + wacc) ** 5)
        implied_equity = implied_ev - debt + cash
        implied_fair_value = implied_equity / shares if shares > 0 else 0

        if implied_fair_value <= 0:
            warnings.append({"level": "critical", "check": "fair_value_negativo",
                             "message": f"Escenario {name}: fair value implícito ≤ 0 "
                                        f"(EV implícito={implied_ev:,.0f}, deuda neta={debt-cash:,.0f})"})
    return warnings


def _check_terminal_value_fraction(v: dict) -> list[dict]:
    """Avisa si el terminal value domina la valoración (>85% del total)."""
    scenarios = v.get("scenarios", {})
    base = scenarios.get("base", {})
    wacc = base.get("wacc", 0)
    tv_multiple = base.get("terminal_multiple", 0)
    latest = v.get("latest_financials", {})
    ebitda = latest.get("ebitda", 0) or 0
    rev = latest.get("revenue", 0) or 0
    gm = base.get("gross_margin", 0) or 0
    sga = base.get("sga_pct", 0) or 0
    rd = base.get("rd_pct", 0) or 0
    da = base.get("da_pct", 0) or 0
    capex = base.get("capex_pct", 0) or 0
    tax = base.get("tax_rate", 0.21) or 0.21
    g1 = base.get("revenue_growth_y1", 0) or 0

    if not all([wacc, tv_multiple, ebitda, rev]):
        return []

    try:
        # Estimar UFCF año 1 para tener referencia
        rev_y1 = rev * (1 + g1)
        ebitda_margin = gm - sga - rd
        ebitda_y1 = rev_y1 * ebitda_margin
        ebit_y1 = ebitda_y1 - rev_y1 * da
        ufcf_y1 = ebitda_y1 - ebit_y1 * tax - rev_y1 * capex

        # Suma simple de UFCF descontados (aprox con UFCF constante)
        pv_ufcf = sum(ufcf_y1 / ((1 + wacc) ** y) for y in range(1, 6))
        pv_tv = (ebitda * tv_multiple) / ((1 + wacc) ** 5)
        total = pv_ufcf + pv_tv

        if total > 0:
            tv_pct = pv_tv / total
            if tv_pct > 0.85:
                return [{"level": "warning", "check": "tv_dominante",
                         "message": f"Terminal Value = {tv_pct:.0%} del valor total. "
                                    f"La valoración depende casi completamente del múltiplo de salida ({tv_multiple:.0f}x)."}]
    except (ZeroDivisionError, TypeError):
        pass
    return []


def _check_revenue_decline_base(v: dict) -> list[dict]:
    """Avisa si el escenario base proyecta caída de revenue en Y1."""
    scenarios = v.get("scenarios", {})
    base = scenarios.get("base", {})
    g1 = base.get("revenue_growth_y1", 0)
    if g1 is not None and g1 < 0:
        return [{"level": "info", "check": "revenue_decline_base",
                 "message": f"Escenario base con revenue decreciente Y1: {g1:.1%}. "
                            f"Verificar que no es un artefacto de datos."}]
    return []


def _check_wacc_range_by_market(v: dict) -> list[dict]:
    """WACC fuera de rango según mercado (desarrollado vs emergente)."""
    scenarios = v.get("scenarios", {})
    ticker = v.get("ticker", "")

    # Inferir mercado del sufijo del ticker
    emerging_suffixes = (".SA", ".MX", ".NS", ".BO", ".IS", ".JK")
    is_emerging = any(ticker.endswith(s) for s in emerging_suffixes)

    wacc_min = 0.04 if not is_emerging else 0.06
    wacc_max = 0.18 if not is_emerging else 0.25

    warnings = []
    for name, sc in scenarios.items():
        wacc = sc.get("wacc", 0)
        if wacc and (wacc < wacc_min or wacc > wacc_max):
            market_type = "emergente" if is_emerging else "desarrollado"
            warnings.append({"level": "warning", "check": "wacc_rango_mercado",
                             "message": f"WACC {name} = {wacc:.1%} fuera de rango para mercado "
                                        f"{market_type} ({wacc_min:.0%}-{wacc_max:.0%})"})
    return warnings
