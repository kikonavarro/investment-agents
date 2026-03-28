"""
Thesis Reviewer — Validación de tesis antes de enviar.
Comprueba consistencia numérica, secciones obligatorias, y errores metodológicos.

Uso:
    python tools/thesis_reviewer.py TSLA
    → JSON con verdict (PASS/REVIEW/FAIL), critical, warnings, info
"""

import json
import re
import sys
from pathlib import Path

VALUATIONS_DIR = Path(__file__).parent.parent / "data" / "valuations"

REQUIRED_SECTIONS = [
    ("Resumen ejecutivo", r"(?i)resumen\s+ejecutivo"),
    ("El negocio", r"(?i)el\s+negocio"),
    ("Análisis financiero", r"(?i)an[aá]lisis\s+financiero"),
    ("Valoración DCF", r"(?i)valoraci[oó]n\s+DCF"),
    ("Riesgos", r"(?i)riesgos"),
    ("Catalizadores", r"(?i)catalizadores"),
    ("Conclusión", r"(?i)conclusi[oó]n"),
]

SENSITIVITY_PATTERN = r"WACC.*TV|WACC.*\\\s*TV|WACC\s*\|"


def review_thesis(ticker: str, thesis_text: str, valuation: dict) -> dict:
    """Ejecuta todos los checks y devuelve el resultado."""
    issues = []

    issues.extend(_check_fair_value_sanity(ticker, thesis_text, valuation))
    issues.extend(_check_extreme_valuation(thesis_text, valuation))
    issues.extend(_check_scenario_spread(thesis_text))
    issues.extend(_check_required_sections(thesis_text))
    issues.extend(_check_sensitivity_table(thesis_text))
    issues.extend(_check_price_consistency(thesis_text, valuation))
    issues.extend(_check_consensus_gap(thesis_text, valuation))
    issues.extend(_check_primary_sources(thesis_text))

    critical = [i for i in issues if i["level"] == "critical"]
    warnings = [i for i in issues if i["level"] == "warning"]
    info = [i for i in issues if i["level"] == "info"]

    if critical:
        verdict = "FAIL"
    elif warnings:
        verdict = "REVIEW"
    else:
        verdict = "PASS"

    summary_parts = []
    if critical:
        summary_parts.append(f"{len(critical)} critical")
    if warnings:
        summary_parts.append(f"{len(warnings)} warnings")
    summary = ", ".join(summary_parts) if summary_parts else "All checks passed"

    return {
        "verdict": verdict,
        "critical": critical,
        "warnings": warnings,
        "info": info,
        "summary": summary,
    }


def _extract_fair_values(thesis_text: str) -> dict:
    """Extrae fair values bear/base/bull de la tesis (tabla markdown)."""
    values = {}
    for scenario in ["bear", "base", "bull"]:
        # Buscar precio en negrita **$XXX** en la fila del escenario
        pattern = rf"\|\s*\**{scenario}\**\s*\|.*?\*\*\$\s*([\d,.]+)\*\*"
        match = re.search(pattern, thesis_text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(",", "")
            try:
                values[scenario] = float(price_str)
            except ValueError:
                pass
        else:
            # Fallback: último $XXX en la fila (suele ser el precio)
            row_pattern = rf"\|\s*\**{scenario}\**\s*\|[^\n]+"
            row_match = re.search(row_pattern, thesis_text, re.IGNORECASE)
            if row_match:
                row = row_match.group(0)
                # Buscar todos los valores $ en la fila, tomar el que parece un precio por acción
                # (no billones: sin B/M después)
                price_matches = re.findall(r"\$\s*([\d,.]+)(?![BMbm])", row)
                if price_matches:
                    price_str = price_matches[-1].replace(",", "")
                    try:
                        values[scenario] = float(price_str)
                    except ValueError:
                        pass
    return values


def _get_ev_ebitda(valuation: dict) -> float:
    """Calcula EV/EBITDA actual."""
    price = valuation.get("current_price", 0)
    shares = valuation.get("shares_outstanding", 0)
    latest = valuation.get("latest_financials", {})
    debt = latest.get("total_debt", 0) or 0
    cash = latest.get("cash", 0) or 0
    ebitda = latest.get("ebitda", 0) or 0

    if not ebitda or ebitda <= 0:
        return 999

    market_cap = price * shares
    ev = market_cap + debt - cash
    return ev / ebitda


# --- Checks ---

def _check_fair_value_sanity(ticker: str, thesis_text: str, valuation: dict) -> list:
    """CRITICAL: Fair values absurdos vs precio de mercado."""
    issues = []
    fv = _extract_fair_values(thesis_text)
    price = valuation.get("current_price", 0)
    ev_ebitda = _get_ev_ebitda(valuation)

    if not fv:
        issues.append({
            "level": "warning",
            "check": "fair_value_extraction",
            "message": "No se pudieron extraer fair values de la tesis. Verificar formato de tabla.",
        })
        return issues

    # Bear check: siempre activo, con umbral ajustado por tipo de empresa
    bear = fv.get("bear", 0)
    if bear and price:
        # EV/EBITDA < 50x: bear > 20% del precio (empresa "normal")
        # EV/EBITDA >= 50x: bear > 5% del precio (empresa de alta valoración, más tolerancia)
        threshold = 0.20 if ev_ebitda < 50 else 0.05
        if bear < price * threshold:
            issues.append({
                "level": "critical",
                "check": "bear_absurdo",
                "message": (
                    f"Bear (${bear:.2f}) es <{threshold:.0%} del precio actual (${price:.2f}). "
                    f"EV/EBITDA={ev_ebitda:.0f}x. Los escenarios son demasiado pesimistas "
                    f"o los múltiplos terminales son incoherentes con el mercado."
                ),
            })

    # Bull < precio actual pero recomienda comprar
    bull = fv.get("bull", 0)
    if bull and bull < price:
        # Buscar recomendación de compra, excluyendo "no comprar"
        recomienda_comprar = bool(re.search(
            r"(?i)(recomendaci[oó]n|se[nñ]al)[^.]*?(comprar|infravalorada|oportunidad)",
            thesis_text
        )) and not bool(re.search(
            r"(?i)(no\s+comprar|sobrevalorada|evitar)",
            thesis_text
        ))
        if recomienda_comprar:
            issues.append({
                "level": "critical",
                "check": "bull_vs_recomendacion",
                "message": (
                    f"Bull (${bull:.2f}) < precio actual (${price:.2f}) pero la tesis "
                    f"recomienda comprar. Inconsistencia grave."
                ),
            })

    return issues


def _check_extreme_valuation(thesis_text: str, valuation: dict) -> list:
    """CRITICAL: Empresa de valoración extrema usando múltiplos automáticos."""
    issues = []
    ev_ebitda = _get_ev_ebitda(valuation)

    if ev_ebitda < 50:
        return issues

    # Extraer múltiplos TV usados en la tesis (buscar Xx en la tabla de escenarios)
    tv_matches = re.findall(r"\b(\d{1,2})x\b", thesis_text)
    tv_values = [int(m) for m in tv_matches if 3 <= int(m) <= 50]

    # También comprobar el JSON (escenarios auto-generados del analyst)
    json_tv = valuation.get("scenarios", {}).get("base", {}).get("terminal_multiple", 0)

    # Determinar el TV máximo usado en la tesis
    max_tv_in_thesis = max(tv_values) if tv_values else json_tv

    if max_tv_in_thesis and max_tv_in_thesis < 20:
        issues.append({
            "level": "critical",
            "check": "multiplos_auto_extrema",
            "message": (
                f"EV/EBITDA actual = {ev_ebitda:.0f}x pero el TV máximo en la tesis = {max_tv_in_thesis}x. "
                f"Parece que se usaron múltiplos de sector estándar. "
                f"Para empresas con EV/EBITDA > 50x, diseñar escenarios manuales con "
                f"múltiplos coherentes (20-35x para tech/growth)."
            ),
        })
    else:
        issues.append({
            "level": "info",
            "check": "valoracion_extrema",
            "message": (
                f"Empresa con valoración extrema (EV/EBITDA = {ev_ebitda:.0f}x). "
                f"TV máximo en tesis = {max_tv_in_thesis}x. Verificar coherencia."
            ),
        })

    return issues


def _check_scenario_spread(thesis_text: str) -> list:
    """WARNING: Ratio bull/bear fuera de rango."""
    issues = []
    fv = _extract_fair_values(thesis_text)

    bear = fv.get("bear", 0)
    bull = fv.get("bull", 0)

    if not bear or not bull or bear <= 0:
        return issues

    ratio = bull / bear

    if ratio < 1.3:
        issues.append({
            "level": "warning",
            "check": "spread_estrecho",
            "message": f"Ratio bull/bear = {ratio:.2f}x (demasiado estrecho, mín 1.5x).",
        })
    elif ratio > 3.5:
        issues.append({
            "level": "warning",
            "check": "spread_amplio",
            "message": f"Ratio bull/bear = {ratio:.2f}x (demasiado amplio, máx 3.0-3.5x).",
        })

    return issues


def _check_required_sections(thesis_text: str) -> list:
    """WARNING: Secciones obligatorias ausentes."""
    issues = []
    for name, pattern in REQUIRED_SECTIONS:
        if not re.search(pattern, thesis_text):
            issues.append({
                "level": "warning",
                "check": "seccion_faltante",
                "message": f"Sección obligatoria no encontrada: '{name}'.",
            })
    return issues


def _check_sensitivity_table(thesis_text: str) -> list:
    """WARNING: Tabla de sensibilidad ausente."""
    if not re.search(SENSITIVITY_PATTERN, thesis_text, re.IGNORECASE):
        return [{
            "level": "warning",
            "check": "tabla_sensibilidad",
            "message": "No se encontró tabla de sensibilidad WACC vs TV Multiple.",
        }]
    return []


def _check_price_consistency(thesis_text: str, valuation: dict) -> list:
    """WARNING: Precio en tesis no coincide con JSON."""
    issues = []
    price = valuation.get("current_price", 0)
    if not price:
        return issues

    # Buscar "Precio actual: $XXX" o "precio actual de $XXX"
    match = re.search(r"(?i)precio\s+actual[:\s]+\$\s*([\d,.]+)", thesis_text)
    if match:
        thesis_price_str = match.group(1).replace(",", "")
        try:
            thesis_price = float(thesis_price_str)
            diff_pct = abs(thesis_price - price) / price
            if diff_pct > 0.02:  # >2% diferencia
                issues.append({
                    "level": "warning",
                    "check": "precio_inconsistente",
                    "message": (
                        f"Precio en tesis (${thesis_price:.2f}) difiere del JSON "
                        f"(${price:.2f}) en {diff_pct:.1%}."
                    ),
                })
        except ValueError:
            pass

    return issues


def _check_consensus_gap(thesis_text: str, valuation: dict) -> list:
    """CRITICAL: Fair value ponderado diverge >80% del consenso de analistas."""
    issues = []
    targets = valuation.get("analyst_targets", {})
    mean_target = targets.get("mean", 0)
    if not mean_target:
        return issues

    fv = _extract_fair_values(thesis_text)
    if not fv or len(fv) < 2:
        return issues

    bear = fv.get("bear", 0)
    base = fv.get("base", 0)
    bull = fv.get("bull", 0)
    if not (bear and base):
        return issues

    weighted = bear * 0.4 + base * 0.4 + bull * 0.2 if bull else bear * 0.5 + base * 0.5
    if weighted > 0 and mean_target > 0:
        ratio = weighted / mean_target
        if ratio < 0.15:
            issues.append({
                "level": "critical",
                "check": "gap_consenso_extremo",
                "message": (
                    f"Fair value ponderado (${weighted:.2f}) es {ratio:.0%} del consenso "
                    f"de analistas (${mean_target:.2f}). Divergencia del {(1-ratio)*100:.0f}%. "
                    f"El DCF es implausible — revisar múltiplos o usar Sum-of-Parts."
                ),
            })
        elif ratio < 0.30:
            issues.append({
                "level": "warning",
                "check": "gap_consenso",
                "message": (
                    f"Fair value ponderado (${weighted:.2f}) está un {(1-ratio)*100:.0f}% "
                    f"por debajo del consenso (${mean_target:.2f}). Verificar supuestos."
                ),
            })
    return issues


def _check_primary_sources(thesis_text: str) -> list:
    """WARNING: Tesis sin referencias a fuentes primarias."""
    source_patterns = [
        r"(?i)10-K", r"(?i)SEC", r"(?i)investor\s+relations",
        r"(?i)IR\b", r"(?i)annual\s+report", r"(?i)informe\s+anual",
        r"(?i)auditor[ií]a\s+SEC", r"(?i)filings?"
    ]
    has_source = any(re.search(p, thesis_text) for p in source_patterns)
    if not has_source:
        return [{
            "level": "warning",
            "check": "sin_fuentes_primarias",
            "message": (
                "Tesis sin referencias a fuentes primarias (10-K, SEC, IR, annual report). "
                "Se recomienda citar datos de filings oficiales."
            ),
        }]
    return []


def print_review(result: dict):
    """Imprime el resultado del review de forma legible."""
    icons = {"PASS": "[OK]", "REVIEW": "[!!]", "FAIL": "[XX]"}
    print(f"\n  {icons[result['verdict']]} Thesis Review: {result['verdict']} — {result['summary']}")

    for issue in result.get("critical", []):
        print(f"    [XX] {issue['check']}: {issue['message']}")
    for issue in result.get("warnings", []):
        print(f"    [!!] {issue['check']}: {issue['message']}")
    for issue in result.get("info", []):
        print(f"    [--] {issue['check']}: {issue['message']}")


# --- CLI ---

def main():
    if len(sys.argv) < 2:
        print("Uso: python tools/thesis_reviewer.py TICKER")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    ticker_dir = VALUATIONS_DIR / ticker

    thesis_path = ticker_dir / f"{ticker}_tesis_inversion.md"
    json_path = ticker_dir / f"{ticker}_valuation.json"

    if not thesis_path.exists():
        print(f"Error: No se encontró tesis en {thesis_path}")
        sys.exit(1)
    if not json_path.exists():
        print(f"Error: No se encontró JSON en {json_path}")
        sys.exit(1)

    thesis_text = thesis_path.read_text(encoding="utf-8")
    valuation = json.loads(json_path.read_text(encoding="utf-8"))

    result = review_thesis(ticker, thesis_text, valuation)

    # Output JSON para uso programático
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_review(result)

    sys.exit(0 if result["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
