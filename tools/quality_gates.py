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

    critical = sum(1 for w in warnings if w["level"] == "critical")
    warning_count = sum(1 for w in warnings if w["level"] == "warning")

    total_checks = 8
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
