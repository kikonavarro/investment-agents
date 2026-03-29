"""
Genera una página HTML estática con el dashboard de valoraciones.
Lee todos los *_valuation.json y calcula fair values con la fórmula DCF corregida.

Uso:
    python tools/web_dashboard.py              # genera data/dashboard.html
    python tools/web_dashboard.py --open       # genera y abre en navegador
"""
import json
import sys
import webbrowser
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
VALUATIONS_DIR = BASE_DIR / "data" / "valuations"
OUTPUT_PATH = BASE_DIR / "data" / "dashboard.html"


def calc_dcf(revenue: float, scenario: dict, net_debt: float, shares: float) -> dict:
    """Calcula fair value con fórmula corregida: UFCF = EBIT×(1-T) + D&A - CapEx, TV sobre EBITDA."""
    growth_rates = [
        scenario['revenue_growth_y1'] + (scenario['revenue_growth_y5'] - scenario['revenue_growth_y1']) * i / 4
        for i in range(5)
    ]

    rev = revenue
    pv_ufcf = 0
    wacc = scenario['wacc']

    for y in range(5):
        rev = rev * (1 + growth_rates[y])
        ebit = rev * (scenario['gross_margin'] - scenario['sga_pct'] - scenario['rd_pct'])
        da = rev * scenario['da_pct']
        ebitda = ebit + da
        capex = rev * scenario['capex_pct']
        ufcf = ebit * (1 - scenario['tax_rate']) + da - capex
        pv_ufcf += ufcf / ((1 + wacc) ** (y + 1))
        if y == 4:
            ebitda_y5 = ebitda

    tv = ebitda_y5 * scenario['terminal_multiple']
    pv_tv = tv / ((1 + wacc) ** 5)
    ev = pv_ufcf + pv_tv
    equity = ev - net_debt
    fair_value = equity / shares if shares > 0 else 0

    return {
        'fair_value': fair_value,
        'ev': ev,
        'tv_pct': pv_tv / ev * 100 if ev > 0 else 0,
    }


def classify_signal(margin_of_safety: float) -> tuple:
    """Returns (emoji, label, css_class)."""
    if margin_of_safety >= 40:
        return ('🟢', 'MUY INFRAVALORADA', 'signal-strong-buy')
    elif margin_of_safety >= 25:
        return ('🟢', 'INFRAVALORADA', 'signal-buy')
    elif margin_of_safety >= 10:
        return ('🟡', 'LIGERAMENTE INFRAVALORADA', 'signal-watchlist')
    elif margin_of_safety >= -10:
        return ('⚪', 'VALOR JUSTO', 'signal-fair')
    elif margin_of_safety >= -25:
        return ('🟠', 'SOBREVALORADA', 'signal-overvalued')
    else:
        return ('🔴', 'MUY SOBREVALORADA', 'signal-avoid')


def load_all_valuations() -> list:
    """Lee todos los JSON de valoración y calcula fair values."""
    results = []

    for json_path in sorted(VALUATIONS_DIR.glob("*/*_valuation.json")):
        if "_2026" in json_path.name:
            continue

        try:
            with open(json_path) as f:
                d = json.load(f)
        except (json.JSONDecodeError, KeyError):
            continue

        if not d.get('scenarios') or not d.get('current_price'):
            continue

        if 'sga_pct' not in d['scenarios'].get('base', {}):
            continue

        revenue = d['latest_financials']['revenue']
        net_debt = d['latest_financials']['total_debt'] - d['latest_financials']['cash']
        shares = d['shares_outstanding']
        price = d['current_price']

        fvs = {}
        for sc_name in ['bear', 'base', 'bull']:
            sc = d['scenarios'].get(sc_name)
            if not sc:
                continue
            result = calc_dcf(revenue, sc, net_debt, shares)
            fvs[sc_name] = result

        if not fvs.get('base'):
            continue

        weighted = (
            0.40 * fvs.get('bear', {}).get('fair_value', 0) +
            0.40 * fvs.get('base', {}).get('fair_value', 0) +
            0.20 * fvs.get('bull', {}).get('fair_value', 0)
        )

        # Si el fair value ponderado es negativo o cero, el DCF no aplica
        # (ej: CapEx > revenue, EBIT negativo, empresas pre-profit)
        dcf_not_applicable = weighted <= 0 or fvs['base']['fair_value'] <= 0

        # Respetar flag dcf_reliable del analyst (validación con auto-corrección)
        if d.get('dcf_reliable') is False:
            dcf_not_applicable = True

        # EV/EBITDA > 50x: el mercado pricea opcionalidad que el DCF no captura
        ebitda_check = d['latest_financials'].get('ebitda', 0)
        if ebitda_check and ebitda_check > 0:
            ev_check = d['market_cap'] + net_debt
            ev_ebitda_check = ev_check / ebitda_check
            if ev_ebitda_check > 50:
                dcf_not_applicable = True

        # D/E > 5x: distress financiero, DCF como going-concern no es fiable
        de_check = d['latest_financials'].get('total_debt', 0) or 0
        mc_check = d.get('market_cap', 0) or 0
        if mc_check > 0 and de_check / mc_check > 5:
            dcf_not_applicable = True

        if dcf_not_applicable:
            mos = 0
            upside = 0
            emoji, label, css_class = ('🟣', 'ESPECULATIVA', 'signal-speculative')
        else:
            mos = (weighted - price) / weighted * 100
            upside = (weighted - price) / price * 100 if price != 0 else 0
            emoji, label, css_class = classify_signal(mos)

        ev_ebitda = 0
        if d['latest_financials'].get('ebitda') and d['latest_financials']['ebitda'] > 0:
            ev_market = d['market_cap'] + net_debt
            ev_ebitda = ev_market / d['latest_financials']['ebitda']

        results.append({
            'ticker': d['ticker'],
            'company': d['company'],
            'sector': d.get('sector', ''),
            'price': price,
            'currency': d.get('currency', '$'),
            'bear': fvs.get('bear', {}).get('fair_value', 0),
            'base': fvs['base']['fair_value'],
            'bull': fvs.get('bull', {}).get('fair_value', 0),
            'weighted': weighted,
            'upside': upside,
            'mos': mos,
            'signal_emoji': emoji,
            'signal_label': label,
            'signal_class': css_class,
            'ev_ebitda': ev_ebitda,
            'market_cap': d['market_cap'],
            'date': d.get('date', ''),
            'wacc_base': d['scenarios']['base']['wacc'],
            'tv_base': d['scenarios']['base']['terminal_multiple'],
        })

    # Especulativas al final, el resto ordenado por upside
    results.sort(key=lambda x: (x['signal_class'] == 'signal-speculative', -x['upside']))
    return results


def generate_html(companies: list) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    rows = ""
    for c in companies:
        is_spec = c['signal_class'] == 'signal-speculative'
        upside_class = "positive" if c['upside'] >= 0 else "negative"

        if is_spec:
            bear_str = "N/A"
            base_str = "N/A"
            bull_str = "N/A"
            weighted_str = "N/A"
            upside_str = "—"
            upside_class = ""
        else:
            bear_str = f"{c['currency']}{c['bear']:.2f}"
            base_str = f"{c['currency']}{c['base']:.2f}"
            bull_str = f"{c['currency']}{c['bull']:.2f}"
            weighted_str = f"{c['currency']}{c['weighted']:.2f}"
            upside_str = f"{c['upside']:+.1f}%"

        rows += f"""
        <tr class="{c['signal_class']}">
            <td class="ticker-cell">
                <span class="ticker">{c['ticker']}</span>
                <span class="company-name">{c['company']}</span>
            </td>
            <td class="sector">{c['sector']}</td>
            <td class="number">{c['currency']}{c['price']:.2f}</td>
            <td class="number bear">{bear_str}</td>
            <td class="number base">{base_str}</td>
            <td class="number bull">{bull_str}</td>
            <td class="number weighted">{weighted_str}</td>
            <td class="number {upside_class}">{upside_str}</td>
            <td class="signal">{c['signal_emoji']} {c['signal_label']}</td>
            <td class="number">{c['ev_ebitda']:.1f}x</td>
            <td class="number">{c['wacc_base']:.1%}</td>
            <td class="number">{c['tv_base']:.0f}x</td>
            <td class="date">{c['date']}</td>
        </tr>"""

    summary_speculative = sum(1 for c in companies if c['signal_class'] == 'signal-speculative')
    non_spec = [c for c in companies if c['signal_class'] != 'signal-speculative']
    summary_buy = sum(1 for c in non_spec if c['mos'] >= 25)
    summary_watchlist = sum(1 for c in non_spec if 10 <= c['mos'] < 25)
    summary_fair = sum(1 for c in non_spec if -10 <= c['mos'] < 10)
    summary_overvalued = sum(1 for c in non_spec if c['mos'] < -10)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Investment Dashboard — Valoraciones DCF</title>
    <style>
        :root {{
            --bg: #0f1117;
            --surface: #1a1d27;
            --surface-hover: #22252f;
            --border: #2a2d3a;
            --text: #e4e4e7;
            --text-muted: #71717a;
            --green: #22c55e;
            --green-dim: #166534;
            --red: #ef4444;
            --red-dim: #991b1b;
            --yellow: #eab308;
            --blue: #3b82f6;
            --orange: #f97316;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            padding: 2rem;
        }}

        h1 {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}

        .subtitle {{
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-bottom: 1.5rem;
        }}

        .summary {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }}

        .summary-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem 1.25rem;
            min-width: 140px;
        }}

        .summary-card .count {{
            font-size: 1.75rem;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }}

        .summary-card .label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .summary-card.buy .count {{ color: var(--green); }}
        .summary-card.watchlist .count {{ color: var(--yellow); }}
        .summary-card.fair .count {{ color: var(--text-muted); }}
        .summary-card.overvalued .count {{ color: var(--red); }}
        .summary-card.speculative .count {{ color: #a855f7; }}

        .table-wrapper {{
            overflow-x: auto;
            border: 1px solid var(--border);
            border-radius: 8px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8125rem;
            white-space: nowrap;
        }}

        thead {{
            background: var(--surface);
            position: sticky;
            top: 0;
            z-index: 1;
        }}

        th {{
            padding: 0.75rem 1rem;
            text-align: left;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 0.6875rem;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border);
        }}

        td {{
            padding: 0.625rem 1rem;
            border-bottom: 1px solid var(--border);
        }}

        tr:hover {{
            background: var(--surface-hover);
        }}

        .ticker-cell {{
            display: flex;
            flex-direction: column;
            gap: 0.125rem;
        }}

        .ticker {{
            font-weight: 700;
            font-size: 0.875rem;
            color: var(--blue);
        }}

        .company-name {{
            font-size: 0.6875rem;
            color: var(--text-muted);
            white-space: normal;
            max-width: 180px;
        }}

        .sector {{
            color: var(--text-muted);
            font-size: 0.75rem;
        }}

        .number {{
            text-align: right;
            font-variant-numeric: tabular-nums;
            font-family: 'JetBrains Mono', 'SF Mono', 'Cascadia Code', monospace;
            font-size: 0.8125rem;
        }}

        .positive {{ color: var(--green); font-weight: 600; }}
        .negative {{ color: var(--red); font-weight: 600; }}

        .bear {{ color: var(--red); opacity: 0.8; }}
        .base {{ color: var(--text); font-weight: 600; }}
        .bull {{ color: var(--green); opacity: 0.8; }}
        .weighted {{ color: var(--blue); font-weight: 700; }}

        .signal {{
            font-size: 0.6875rem;
            font-weight: 500;
            white-space: nowrap;
        }}

        .signal-strong-buy .signal {{ color: var(--green); }}
        .signal-buy .signal {{ color: var(--green); }}
        .signal-watchlist .signal {{ color: var(--yellow); }}
        .signal-fair .signal {{ color: var(--text-muted); }}
        .signal-overvalued .signal {{ color: var(--orange); }}
        .signal-avoid .signal {{ color: var(--red); }}
        .signal-speculative .signal {{ color: #a855f7; }}

        .date {{
            color: var(--text-muted);
            font-size: 0.75rem;
        }}

        .footer {{
            margin-top: 1.5rem;
            color: var(--text-muted);
            font-size: 0.75rem;
            text-align: center;
        }}

        .methodology {{
            margin-top: 1rem;
            padding: 1rem;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.75rem;
            color: var(--text-muted);
        }}

        .methodology strong {{
            color: var(--text);
        }}

        @media (max-width: 768px) {{
            body {{ padding: 1rem; }}
            .summary {{ gap: 0.5rem; }}
            .summary-card {{ min-width: 100px; padding: 0.75rem; }}
            .summary-card .count {{ font-size: 1.25rem; }}
        }}
    </style>
</head>
<body>
    <h1>Investment Dashboard</h1>
    <p class="subtitle">Valoraciones DCF — {len(companies)} empresas analizadas — Actualizado {now}</p>

    <div class="summary">
        <div class="summary-card buy">
            <div class="count">{summary_buy}</div>
            <div class="label">Infravaloradas (MoS &ge;25%)</div>
        </div>
        <div class="summary-card watchlist">
            <div class="count">{summary_watchlist}</div>
            <div class="label">Watchlist (10-25%)</div>
        </div>
        <div class="summary-card fair">
            <div class="count">{summary_fair}</div>
            <div class="label">Valor justo (&plusmn;10%)</div>
        </div>
        <div class="summary-card overvalued">
            <div class="count">{summary_overvalued}</div>
            <div class="label">Sobrevaloradas</div>
        </div>
        <div class="summary-card speculative">
            <div class="count">{summary_speculative}</div>
            <div class="label">Especulativas (DCF N/A)</div>
        </div>
    </div>

    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>Empresa</th>
                    <th>Sector</th>
                    <th style="text-align:right">Precio</th>
                    <th style="text-align:right">Bear</th>
                    <th style="text-align:right">Base</th>
                    <th style="text-align:right">Bull</th>
                    <th style="text-align:right">Ponderado</th>
                    <th style="text-align:right">Potencial</th>
                    <th>Signal</th>
                    <th style="text-align:right">EV/EBITDA</th>
                    <th style="text-align:right">WACC</th>
                    <th style="text-align:right">TV Exit</th>
                    <th>Fecha</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>

    <div class="methodology">
        <strong>Metodologia:</strong> DCF 5 anos, UFCF = EBIT&times;(1-T) + D&amp;A - CapEx, Terminal Value = EBITDA<sub>Y5</sub> &times; EV/EBITDA exit multiple.
        Ponderado: 40% Bear + 40% Base + 20% Bull. Senal basada en margen de seguridad (MoS).
        Los growth rates se aplican con haircut por market cap (max 8% large cap, 12% mid, 15% small). Datos: Yahoo Finance + SEC 10-K.
    </div>

    <p class="footer">No es consejo de inversion. Analisis personal generado automaticamente.</p>
</body>
</html>"""


def main():
    companies = load_all_valuations()
    html = generate_html(companies)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard generado: {OUTPUT_PATH} ({len(companies)} empresas)")

    if "--open" in sys.argv:
        webbrowser.open(f"file://{OUTPUT_PATH}")


if __name__ == "__main__":
    main()
