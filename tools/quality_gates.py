"""
Quality Gates — validaciones de datos crudos post-analyst.
Solo valida calidad de datos. NO valida escenarios ni fair values
(eso lo hace Opus al escribir la tesis).
"""


def validate_valuation(valuation: dict) -> dict:
    """
    Ejecuta validaciones sobre el JSON de datos crudos.

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
    warnings.extend(_check_historical_depth(valuation))
    warnings.extend(_check_shares(valuation))
    warnings.extend(_check_debt_sanity(valuation))
    warnings.extend(_check_extreme_valuation(valuation))
    warnings.extend(_check_captive_finance(valuation))
    warnings.extend(_check_acquisition_detected(valuation))

    critical = sum(1 for w in warnings if w["level"] == "critical")
    warning_count = sum(1 for w in warnings if w["level"] == "warning")

    total_checks = 9
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


# --- Checks de datos crudos ---

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
    equity = latest.get("total_equity", 0) or 0
    # Usar deuda industrial si hay banco cautivo
    metrics = v.get("reference_metrics", {})
    captive = metrics.get("captive_finance") if metrics else None
    if not captive:
        captive = v.get("captive_finance")
    if captive and captive.get("detected"):
        debt = captive.get("estimated_industrial_debt", 0) or 0
    else:
        debt = latest.get("total_debt", 0) or 0
    if equity > 0 and debt / equity > 5:
        return [{"level": "warning", "check": "deuda",
                 "message": f"Ratio deuda/equity muy alto: {debt/equity:.1f}x"}]
    if equity < 0:
        return [{"level": "warning", "check": "patrimonio",
                 "message": "Patrimonio neto negativo"}]
    return []


def _check_extreme_valuation(v: dict) -> list[dict]:
    """Señala narrative stocks (EV/EBITDA > 50x)."""
    price = v.get("current_price", 0)
    shares = v.get("shares_outstanding", 0)
    latest = v.get("latest_financials", {})
    ebitda = latest.get("ebitda", 0) or 0

    if not ebitda or ebitda <= 0 or not price or not shares:
        return []

    # Usar EV/EBITDA de metrics si disponible
    metrics = v.get("reference_metrics", {})
    ev_ebitda = metrics.get("ev_ebitda") if metrics else None
    if not ev_ebitda:
        debt = latest.get("total_debt", 0) or 0
        cash = latest.get("cash", 0) or 0
        market_cap = price * shares
        ev_ebitda = (market_cap + debt - cash) / ebitda

    if ev_ebitda > 50:
        return [{"level": "info", "check": "valoracion_extrema",
                 "message": (
                     f"EV/EBITDA = {ev_ebitda:.0f}x (>50x). Narrative stock — "
                     f"considerar Sum-of-Parts o análisis cualitativo en la tesis."
                 )}]
    return []


def _check_captive_finance(v: dict) -> list[dict]:
    """Alerta si se detectó un banco cautivo."""
    metrics = v.get("reference_metrics", {})
    captive = metrics.get("captive_finance") if metrics else None
    if not captive:
        captive = v.get("captive_finance")
    if captive and captive.get("detected"):
        total_debt = captive.get("total_debt", 0)
        industrial_debt = captive.get("estimated_industrial_debt", 0)
        return [{"level": "info", "check": "banco_cautivo",
                 "message": (
                     f"Banco cautivo detectado. Deuda total {total_debt/1e6:,.0f}M incluye "
                     f"préstamos Financial Services. Deuda industrial estimada: ~{industrial_debt/1e6:,.0f}M. "
                     f"Usar deuda industrial (no total) en el DCF de la tesis."
                 )}]
    return []


def _check_acquisition_detected(v: dict) -> list[dict]:
    """Alerta si se detectó una posible adquisición."""
    metrics = v.get("reference_metrics", {})
    acq = metrics.get("acquisition_detected") if metrics else None
    if not acq:
        acq = v.get("acquisition_detected")
    if acq and acq.get("detected"):
        jump = acq.get("jump_pct", 0)
        year = acq.get("year", "?")
        return [{"level": "info", "check": "adquisicion_detectada",
                 "message": (
                     f"Revenue saltó {jump:.0%} en {year}. Probable adquisición. "
                     f"Usar tasas orgánicas de crecimiento en la tesis."
                 )}]
    return []
