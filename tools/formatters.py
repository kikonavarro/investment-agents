"""
Compresores de datos para minimizar tokens enviados a Claude.
REGLA: Nunca envíes un DataFrame completo. Envía un resumen compacto.
"""


def format_financials_for_llm(financials: dict, dcf_report: str) -> str:
    """
    Comprime datos de extract_financials() + DCF report para Claude.

    Args:
        financials: dict plano de extract_financials()
        dcf_report: string formateado de format_dcf_report()

    Output ejemplo:
        AAPL | Apple Inc | Technology | USD
        Precio: $185.50 | MCap: $2,870B
        === MÉTRICAS CLAVE ===
        Revenue: $394B | Net Income: $97B | FCF: $99B
        Revenue ($B): 274→294→365→383→394
        FCF ($B): 73→80→93→111→99
        Margins: Gross 44% | Op 30% | Net 25% | FCF 25%
        ROIC: 56% | ROE: 147% | D/E: 1.8
        P/E: 29.5 | P/B: 45.2 | FCF Yield: 3.5%
        Rev CAGR 5Y: 7.8% | FCF CAGR 5Y: 6.2%
        === DCF VALUATION ===
        [full DCF report with scenarios, sensitivity, sanity checks]
    """
    f = financials
    lines = []

    # --- Header ---
    lines.append(f"{f['ticker']} | {f['name']} | {f['sector']} | {f['currency']}")

    price_str = f"{f['current_price']:,.2f}" if f.get("current_price") else "N/A"
    mcap_str = _format_large_number(f["market_cap"]) if f.get("market_cap") else "N/A"
    lines.append(f"Precio: {price_str} | MCap: {mcap_str}")

    # --- Key financials ---
    lines.append("=== MÉTRICAS CLAVE ===")
    lines.append(
        f"Revenue: {_format_large_number(f['revenue'])} | "
        f"Net Income: {_format_large_number(f['net_income'])} | "
        f"FCF: {_format_large_number(f['fcf'])}"
    )

    # Revenue history (arrows)
    rev_hist = f.get("revenue_history", [])
    if len(rev_hist) >= 2:
        arrow = "->".join(f"{v/1e9:.0f}" for v in rev_hist[-5:])
        lines.append(f"Revenue ($B): {arrow}")

    # FCF history (arrows)
    fcf_hist = f.get("fcf_history", [])
    if len(fcf_hist) >= 2:
        arrow = "->".join(f"{v/1e9:.0f}" for v in fcf_hist[-5:])
        lines.append(f"FCF ($B): {arrow}")

    # Margins
    lines.append(
        f"Margins: Gross {f['gross_margin']:.0%} | Op {f['operating_margin']:.0%} | "
        f"Net {f['net_margin']:.0%} | FCF {f['fcf_margin']:.0%}"
    )

    # Ratios
    de_str = f"{f['debt_to_equity']:.1f}" if f['debt_to_equity'] < 100 else "N/A"
    lines.append(f"ROIC: {f['roic']:.0%} | ROE: {f['roe']:.0%} | D/E: {de_str}")

    pe_str = f"{f['pe']:.1f}" if f['pe'] < 500 else "N/A"
    pb_str = f"{f['pb']:.1f}" if f['pb'] < 500 else "N/A"
    lines.append(f"P/E: {pe_str} | P/B: {pb_str} | FCF Yield: {f['fcf_yield']:.1%}")

    lines.append(f"Rev CAGR 5Y: {f['revenue_cagr_5y']:.1%} | FCF CAGR 5Y: {f['fcf_cagr_5y']:.1%}")

    # --- DCF report ---
    lines.append("")
    lines.append(dcf_report)

    return "\n".join(lines)


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


def _growth_to_arrow(growth: dict) -> str:
    """{'2021': 0.073, '2022': 0.241} → '7%→24%'"""
    years = sorted(growth.keys())
    values = [f"{growth[y]:.0%}" for y in years]
    return "→".join(values)
