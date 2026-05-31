"""
Compresores de datos para minimizar tokens enviados a Claude.
REGLA: Nunca envíes un DataFrame completo. Envía un resumen compacto.
"""


def format_portfolio_for_llm(portfolio_data: list[dict]) -> str:
    """
    Comprime estado de cartera a ~200 tokens.

    Output ejemplo:
        CARTERA | 5 posiciones | Valor: €47,320 | P&L: +8.2%
        Ticker    | Peso  | P&L%   | vs Target
        BATS.L    | 25%   | +12.3% | -15% (margen)
        SAN.MC    | 20%   | -3.2%  | -28% (margen)
    """
    if not portfolio_data:
        return "CARTERA VACÍA"

    total_value = sum(p.get("current", 0) for p in portfolio_data)
    total_invested = sum(p.get("invested", 0) for p in portfolio_data)
    total_pnl = ((total_value - total_invested) / total_invested * 100) if total_invested else 0

    lines = [f"CARTERA | {len(portfolio_data)} posiciones | Valor: {total_value:,.0f} | P&L: {total_pnl:+.1f}%"]
    lines.append("Nombre | Peso | P&L% | Notas")

    for p in portfolio_data:
        weight = (p["current"] / total_value * 100) if total_value else 0
        pnl = p.get("pnl_pct", 0)
        notes = ""
        if p.get("needs_update"):
            notes = "ACTUALIZAR"
        elif p.get("source") == "manual":
            notes = "manual"

        lines.append(f"{p['name'][:18]:18s} | {weight:4.0f}% | {pnl:+6.1f}% | {notes}")

    return "\n".join(lines)


def format_screener_results_for_llm(candidates: list[dict]) -> str:
    """
    Comprime resultados del screener a ~400 tokens para 10-15 empresas.
    """
    if not candidates:
        return "SCREENING: 0 candidatas encontradas"

    lines = [f"SCREENING | {len(candidates)} candidatas"]
    lines.append("Ticker | Sector | P/E | P/B | D/E | FCF Yield | ROIC")

    for c in candidates:
        pe = f"{c.get('pe', 0):.1f}" if c.get("pe") else "N/A"
        pb = f"{c.get('pb', 0):.1f}" if c.get("pb") else "N/A"
        de = f"{c.get('de', 0):.1f}" if c.get("de") else "N/A"
        fcf_y = f"{c.get('fcf_yield', 0):.1%}" if c.get("fcf_yield") else "N/A"
        roic = f"{c.get('roic', 0):.0%}" if c.get("roic") else "N/A"
        sector = c.get("sector", "N/A")[:12]

        lines.append(f"{c['ticker']:8s} | {sector:12s} | {pe:5s} | {pb:4s} | {de:4s} | {fcf_y:9s} | {roic}")

    return "\n".join(lines)


def format_comparison_for_llm(val1: dict, val2: dict) -> str:
    """
    Comprime dos valoraciones para comparación lado a lado.
    Usado por el skill `comparator` y el flag --compare.
    """
    lines = [f"COMPARACIÓN | {val1.get('ticker', '?')} vs {val2.get('ticker', '?')}"]
    lines.append("")

    header = f"{'Métrica':25s} | {val1.get('ticker', '?'):>12s} | {val2.get('ticker', '?'):>12s}"
    lines.append(header)
    lines.append("-" * len(header))

    # Datos básicos
    for label, key in [
        ("Precio", "current_price"),
        ("Market Cap", "market_cap"),
    ]:
        v1 = val1.get(key, 0)
        v2 = val2.get(key, 0)
        if key == "market_cap":
            lines.append(f"{label:25s} | {_format_large_number(v1):>12s} | {_format_large_number(v2):>12s}")
        else:
            lines.append(f"{label:25s} | {v1:>12,.2f} | {v2:>12,.2f}")

    lines.append(f"{'Sector':25s} | {val1.get('sector', 'N/A'):>12s} | {val2.get('sector', 'N/A'):>12s}")
    lines.append(f"{'Moneda':25s} | {val1.get('currency', '$'):>12s} | {val2.get('currency', '$'):>12s}")

    # Financials
    lines.append("")
    for label, key in [
        ("Revenue", "revenue"),
        ("Net Income", "net_income"),
        ("EBITDA", "ebitda"),
        ("FCF", "free_cashflow"),
    ]:
        v1 = val1.get("latest_financials", {}).get(key, 0)
        v2 = val2.get("latest_financials", {}).get(key, 0)
        lines.append(f"{label:25s} | {_format_large_number(v1):>12s} | {_format_large_number(v2):>12s}")

    for label, key in [
        ("Margen bruto", "gross_margin"),
        ("Margen operativo", "operating_margin"),
        ("Margen neto", "net_margin"),
    ]:
        v1 = val1.get("latest_financials", {}).get(key, 0)
        v2 = val2.get("latest_financials", {}).get(key, 0)
        lines.append(f"{label:25s} | {v1:>11.1%} | {v2:>11.1%}")

    # Métricas de referencia
    lines.append("")
    m1 = val1.get("reference_metrics", {})
    m2 = val2.get("reference_metrics", {})
    for label, key, fmt in [
        ("EV/EBITDA", "ev_ebitda", "{:>11.1f}x"),
        ("Avg Growth", "avg_growth", "{:>11.1%}"),
        ("Beta", "beta", "{:>12.2f}"),
    ]:
        v1 = m1.get(key, 0) or 0
        v2 = m2.get(key, 0) or 0
        lines.append(f"{label:25s} | {fmt.format(v1)} | {fmt.format(v2)}")

    return "\n".join(lines)


# --- Helpers ---

def _format_large_number(n: float) -> str:
    """1_500_000_000 → '1,500B'"""
    if n >= 1e12:
        return f"${n / 1e12:,.1f}T"
    if n >= 1e9:
        return f"${n / 1e9:,.0f}B"
    if n >= 1e6:
        return f"${n / 1e6:,.0f}M"
    return f"${n:,.0f}"


def _series_to_arrow(series: dict, divisor: float = 1) -> str:
    """{'2020': 274e9, '2021': 294e9} → '274→294'"""
    years = sorted(series.keys())
    values = [f"{series[y] / divisor:.0f}" for y in years]
    return "→".join(values)

