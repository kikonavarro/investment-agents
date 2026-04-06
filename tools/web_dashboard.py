"""
Genera una página HTML estática con el dashboard de valoraciones + tesis embebidas.
Lee todos los *_valuation.json y calcula fair values con la fórmula DCF corregida.
Embebe tesis markdown con diseño premium.

Uso:
    python tools/web_dashboard.py              # genera data/dashboard.html
    python tools/web_dashboard.py --open       # genera y abre en navegador
"""
import json
import sys
import webbrowser
import re
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


def markdown_to_html(text: str) -> str:
    """Convierte markdown básico a HTML."""
    # Escapar HTML
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Headings
    text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)

    # Código inline
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.*?)__', r'<strong>\1</strong>', text)

    # Italic
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_(.*?)_', r'<em>\1</em>', text)

    # Párrafos (doble salto de línea)
    text = re.sub(r'\n\n+', '</p><p>', text)
    text = f'<p>{text}</p>'

    # Listas
    text = re.sub(r'<p>- (.*?)</p>', r'<ul><li>\1</li></ul>', text, flags=re.MULTILINE)
    text = re.sub(r'</ul><p>- (.*?)</p><ul>', r'<li>\1</li>', text)

    # Links
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)

    # Tablas markdown
    table_pattern = r'\|.*\|.*\n.*---.*\n((\|.*\n)+)'
    if re.search(table_pattern, text):
        text = re.sub(table_pattern, r'<table class="data-table">\1</table>', text)
        text = re.sub(r'<table class="data-table">(\|.*\n)+</table>',
                     lambda m: _convert_table_row(m.group(0)), text)

    return text


def _convert_table_row(table_html: str) -> str:
    """Convierte filas markdown de tabla a HTML <tr><td>."""
    lines = table_html.strip().split('\n')
    result = '<table class="data-table"><thead><tr>'

    # Headers (primera fila)
    headers = [h.strip() for h in lines[0].split('|') if h.strip()]
    for h in headers:
        result += f'<th>{h}</th>'
    result += '</tr></thead><tbody>'

    # Filas (ignorar separador de dashes)
    for line in lines[2:]:
        if '---' not in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            result += '<tr>'
            for cell in cells:
                result += f'<td>{cell}</td>'
            result += '</tr>'

    result += '</tbody></table>'
    return result


def load_thesis(ticker: str) -> str:
    """Lee la tesis markdown de una empresa."""
    thesis_path = VALUATIONS_DIR / ticker / f"{ticker}_tesis_inversion.md"
    if not thesis_path.exists():
        return ""

    try:
        content = thesis_path.read_text(encoding="utf-8")
        # Extraer solo hasta "---" si hay múltiples, o todo
        parts = content.split('---')
        if len(parts) > 1:
            content = '---'.join(parts[1:])  # Saltarse frontmatter si existe
        return markdown_to_html(content)
    except Exception as e:
        return f"<p class='error'>Error cargando tesis: {e}</p>"


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
    """Lee todos los JSON de valoración + fair values de history.json (escritos por Opus)."""
    results = []

    for json_path in sorted(VALUATIONS_DIR.glob("*/*_valuation.json")):
        if "_2026" in json_path.name:
            continue

        try:
            with open(json_path) as f:
                d = json.load(f)
        except (json.JSONDecodeError, KeyError):
            continue

        if not d.get('current_price'):
            continue

        price = d['current_price']

        # Leer fair values de history.json (escritos por Opus al hacer tesis)
        history_path = json_path.parent / "history.json"
        bear, base, bull = 0, 0, 0
        has_fair_values = False
        if history_path.exists():
            try:
                history = json.loads(history_path.read_text(encoding="utf-8"))
                if history:
                    latest = history[-1]
                    bear = latest.get("fair_value_bear", 0) or 0
                    base = latest.get("fair_value_base", 0) or 0
                    bull = latest.get("fair_value_bull", 0) or 0
                    has_fair_values = base > 0
            except Exception:
                pass

        if has_fair_values:
            weighted = 0.40 * bear + 0.40 * base + 0.20 * bull
            mos = (weighted - price) / weighted * 100 if weighted > 0 else 0
            upside = (weighted - price) / price * 100 if price != 0 else 0
            emoji, label, css_class = classify_signal(mos)
        else:
            weighted, mos, upside = 0, 0, 0
            emoji, label, css_class = ('⚪', 'PENDIENTE', 'signal-speculative')

        net_debt = (d.get('latest_financials', {}).get('total_debt', 0) or 0) - \
                   (d.get('latest_financials', {}).get('cash', 0) or 0)
        ev_ebitda = 0
        ebitda = d.get('latest_financials', {}).get('ebitda', 0) or 0
        if ebitda > 0:
            ev_market = (d.get('market_cap', 0) or 0) + net_debt
            ev_ebitda = ev_market / ebitda

        wacc_base = 0
        tv_base = 0
        if d.get('scenarios', {}).get('base'):
            wacc_base = d['scenarios']['base'].get('wacc', 0)
            tv_base = d['scenarios']['base'].get('terminal_multiple', 0)

        results.append({
            'ticker': d['ticker'],
            'company': d['company'],
            'sector': d.get('sector', ''),
            'price': price,
            'currency': d.get('currency', '$'),
            'bear': bear,
            'base': base,
            'bull': bull,
            'weighted': weighted,
            'upside': upside,
            'mos': mos,
            'signal_emoji': emoji,
            'signal_label': label,
            'signal_class': css_class,
            'ev_ebitda': ev_ebitda,
            'market_cap': d.get('market_cap', 0),
            'date': d.get('date', ''),
            'wacc_base': wacc_base,
            'tv_base': tv_base,
            'thesis_html': load_thesis(d['ticker']),
        })

    results.sort(key=lambda x: (x['signal_class'] == 'signal-speculative', -x['upside']))
    return results


def generate_html(companies: list) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    rows = ""
    modals = ""
    for idx, c in enumerate(companies):
        is_spec = c['signal_class'] == 'signal-speculative'
        upside_class = "positive" if c['upside'] >= 0 else "negative"
        modal_id = f"modal-{c['ticker']}"

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
        <tr class="{c['signal_class']}" onclick="openModal('{modal_id}')" style="cursor:pointer;">
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

        # Modal con tesis
        thesis_content = c.get('thesis_html', '<p>Sin tesis disponible.</p>')
        modals += f"""
    <div id="{modal_id}" class="modal">
        <div class="modal-overlay" onclick="closeModal('{modal_id}')"></div>
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <h2>{c['ticker']} — {c['company']}</h2>
                    <p class="modal-subtitle">{c['sector']} • {c['currency']}{c['price']:.2f}</p>
                </div>
                <button class="close-btn" onclick="closeModal('{modal_id}')">&times;</button>
            </div>
            <div class="modal-body thesis-content">
                {thesis_content}
            </div>
        </div>
    </div>"""

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
    <title>Investment Dashboard — Análisis de Valor</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap');

        :root {{
            --bg: #0a0e27;
            --bg-secondary: #0f1220;
            --surface: #151b3a;
            --surface-hover: #1e2447;
            --border: #2a3154;
            --text: #e8eaf6;
            --text-muted: #9ca3af;
            --green: #10b981;
            --red: #ef4444;
            --yellow: #f59e0b;
            --blue: #3b82f6;
            --purple: #8b5cf6;
            --orange: #f97316;
            --accent: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        html {{ scroll-behavior: smooth; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 3rem 2rem;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}

        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: var(--accent);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .header {{
            margin-bottom: 3rem;
        }}

        .subtitle {{
            color: var(--text-muted);
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}

        .summary-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}

        .summary-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--accent);
            transform: scaleX(0);
            transition: transform 0.3s;
            transform-origin: left;
        }}

        .summary-card:hover {{
            border-color: var(--blue);
            background: var(--surface-hover);
            transform: translateY(-2px);
        }}

        .summary-card:hover::before {{
            transform: scaleX(1);
        }}

        .summary-card .count {{
            font-size: 2rem;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            margin-bottom: 0.5rem;
        }}

        .summary-card .label {{
            font-size: 0.875rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 500;
        }}

        .summary-card.buy .count {{ color: var(--green); }}
        .summary-card.watchlist .count {{ color: var(--yellow); }}
        .summary-card.fair .count {{ color: var(--text-muted); }}
        .summary-card.overvalued .count {{ color: var(--orange); }}
        .summary-card.speculative .count {{ color: var(--purple); }}

        .table-wrapper {{
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            background: var(--surface);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }}

        thead {{
            background: linear-gradient(to right, var(--surface), var(--surface-hover));
            position: sticky;
            top: 0;
            z-index: 10;
        }}

        th {{
            padding: 1rem 1.25rem;
            text-align: left;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.08em;
            border-bottom: 2px solid var(--border);
        }}

        td {{
            padding: 0.875rem 1.25rem;
            border-bottom: 1px solid var(--border);
        }}

        tbody tr {{
            transition: all 0.2s;
            cursor: pointer;
        }}

        tbody tr:hover {{
            background: var(--surface-hover);
            border-left: 3px solid var(--blue);
        }}

        .ticker-cell {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }}

        .ticker {{
            font-weight: 700;
            font-size: 0.95rem;
            color: var(--blue);
        }}

        .company-name {{
            font-size: 0.75rem;
            color: var(--text-muted);
            white-space: normal;
            max-width: 180px;
        }}

        .sector {{
            color: var(--text-muted);
            font-size: 0.8rem;
        }}

        .number {{
            text-align: right;
            font-variant-numeric: tabular-nums;
            font-family: 'Geist Mono', 'SF Mono', monospace;
            font-size: 0.875rem;
        }}

        .positive {{ color: var(--green); font-weight: 600; }}
        .negative {{ color: var(--red); font-weight: 600; }}

        .bear {{ color: var(--red); opacity: 0.75; }}
        .base {{ color: var(--text); font-weight: 600; }}
        .bull {{ color: var(--green); opacity: 0.75; }}
        .weighted {{ color: var(--blue); font-weight: 700; }}

        .signal {{
            font-size: 0.75rem;
            font-weight: 600;
            white-space: nowrap;
        }}

        .date {{
            color: var(--text-muted);
            font-size: 0.75rem;
        }}

        /* Modales */
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 1000;
        }}

        .modal.active {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .modal-overlay {{
            position: absolute;
            inset: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(4px);
        }}

        .modal-content {{
            position: relative;
            z-index: 1001;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            width: 90%;
            max-width: 800px;
            max-height: 85vh;
            overflow-y: auto;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
            animation: slideIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }}

        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: scale(0.95) translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: scale(1) translateY(0);
            }}
        }}

        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 2rem;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(to right, var(--surface), var(--surface-hover));
        }}

        .modal-header h2 {{
            font-size: 1.75rem;
            margin-bottom: 0.5rem;
        }}

        .modal-subtitle {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}

        .close-btn {{
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 2rem;
            cursor: pointer;
            line-height: 1;
            padding: 0;
            transition: color 0.2s;
            flex-shrink: 0;
        }}

        .close-btn:hover {{
            color: var(--text);
        }}

        .modal-body {{
            padding: 2rem;
            overflow-y: auto;
            max-height: calc(85vh - 150px);
        }}

        .thesis-content {{
            font-size: 0.95rem;
            line-height: 1.8;
        }}

        .thesis-content h1 {{
            background: none;
            -webkit-text-fill-color: unset;
            background-clip: unset;
            font-size: 1.75rem;
            margin: 1.5rem 0 0.75rem 0;
            color: var(--text);
        }}

        .thesis-content h2 {{
            font-size: 1.35rem;
            margin: 1.5rem 0 0.75rem 0;
            color: var(--blue);
        }}

        .thesis-content h3 {{
            font-size: 1.1rem;
            margin: 1rem 0 0.5rem 0;
            color: var(--text);
        }}

        .thesis-content p {{
            margin-bottom: 1rem;
            color: var(--text);
        }}

        .thesis-content strong {{
            color: var(--text);
            font-weight: 600;
        }}

        .thesis-content code {{
            background: var(--bg);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: 'Geist Mono', monospace;
            color: var(--yellow);
        }}

        .thesis-content ul, .thesis-content ol {{
            margin: 1rem 0 1rem 1.5rem;
            color: var(--text);
        }}

        .thesis-content li {{
            margin-bottom: 0.5rem;
        }}

        .thesis-content table.data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            font-size: 0.9rem;
        }}

        .thesis-content table.data-table th {{
            background: var(--bg-secondary);
            padding: 0.75rem;
            text-align: left;
            border: 1px solid var(--border);
            font-weight: 600;
        }}

        .thesis-content table.data-table td {{
            padding: 0.75rem;
            border: 1px solid var(--border);
        }}

        .thesis-content table.data-table tr:nth-child(even) {{
            background: var(--bg-secondary);
        }}

        .methodology {{
            margin-top: 3rem;
            padding: 1.5rem;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            font-size: 0.875rem;
            color: var(--text-muted);
            line-height: 1.7;
        }}

        .methodology strong {{
            color: var(--text);
        }}

        .footer {{
            margin-top: 2.5rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.8rem;
        }}

        @media (max-width: 768px) {{
            body {{ padding: 1rem; }}
            h1 {{ font-size: 1.75rem; }}
            .summary {{ grid-template-columns: 1fr; }}
            .modal-content {{
                width: 95%;
                max-height: 90vh;
            }}
            .modal-header {{
                flex-direction: column;
                gap: 1rem;
            }}
            .modal-header h2 {{
                font-size: 1.25rem;
            }}
            table {{ font-size: 0.75rem; }}
            td, th {{ padding: 0.5rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Investment Dashboard</h1>
            <p class="subtitle">Análisis de Valor — {len(companies)} empresas analizadas</p>
            <p class="subtitle" style="font-size: 0.85rem;">Actualizado {now}</p>
        </div>

        <div class="summary">
            <div class="summary-card buy" onclick="filterByClass('signal-buy')" style="cursor:pointer;">
                <div class="count">{summary_buy}</div>
                <div class="label">Infravaloradas</div>
            </div>
            <div class="summary-card watchlist" onclick="filterByClass('signal-watchlist')" style="cursor:pointer;">
                <div class="count">{summary_watchlist}</div>
                <div class="label">Watchlist</div>
            </div>
            <div class="summary-card fair" onclick="filterByClass('signal-fair')" style="cursor:pointer;">
                <div class="count">{summary_fair}</div>
                <div class="label">Valor Justo</div>
            </div>
            <div class="summary-card overvalued" onclick="filterByClass('signal-overvalued')" style="cursor:pointer;">
                <div class="count">{summary_overvalued}</div>
                <div class="label">Sobrevaloradas</div>
            </div>
            <div class="summary-card speculative" onclick="filterByClass('signal-speculative')" style="cursor:pointer;">
                <div class="count">{summary_speculative}</div>
                <div class="label">Especulativas</div>
            </div>
            <div class="summary-card" onclick="clearFilter()" style="cursor:pointer; border: 1px dashed var(--border);">
                <div class="count" style="font-size: 1.2rem;">✕</div>
                <div class="label">Limpiar Filtro</div>
            </div>
        </div>
        <div id="filter-indicator" style="display:none; text-align:center; margin-bottom:1rem; color:var(--text-muted); font-size:0.9rem;">
            Mostrando: <strong id="filter-name"></strong> | <a href="#" onclick="clearFilter(); return false;" style="color:var(--blue); text-decoration:underline;">Limpiar</a>
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
                        <th>Señal</th>
                        <th style="text-align:right">EV/EBITDA</th>
                        <th style="text-align:right">WACC</th>
                        <th style="text-align:right">TV</th>
                        <th>Fecha</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>

        <div class="methodology">
            <strong>Metodología:</strong> Valuación por Descuento de Flujos de Caja (DCF) a 5 años.
            <strong>UFCF</strong> = EBIT×(1-Tasa Fiscal) + D&amp;A − CapEx.
            <strong>Terminal Value</strong> = EBITDA<sub>Y5</sub> × múltiplo de salida por sector.
            <strong>Fair Value</strong> = 40% Bear + 40% Base + 20% Bull.
            <strong>Señal</strong> se basa en margen de seguridad (MoS): precio vs. fair value ponderado.
            Datos: Yahoo Finance, SEC 10-K, estimaciones analistas.
        </div>

        <p class="footer">
            ⚠️ Análisis personal con fines educativos. No es recomendación de inversión.
            Generado automáticamente. Revisar siempre los supuestos antes de invertir.
        </p>
    </div>

    {modals}

    <script>
        function openModal(modalId) {{
            const modal = document.getElementById(modalId);
            if (modal) {{
                modal.classList.add('active');
                document.body.style.overflow = 'hidden';
            }}
        }}

        function closeModal(modalId) {{
            const modal = document.getElementById(modalId);
            if (modal) {{
                modal.classList.remove('active');
                document.body.style.overflow = '';
            }}
        }}

        // Cerrar modal al presionar Escape
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                document.querySelectorAll('.modal.active').forEach(m => {{
                    m.classList.remove('active');
                }});
                document.body.style.overflow = '';
            }}
        }});

        // Filtrado de tabla
        let currentFilter = null;

        function filterByClass(className) {{
            const table = document.querySelector('tbody');
            const rows = table.querySelectorAll('tr');
            let visibleCount = 0;

            rows.forEach(row => {{
                if (row.classList.contains(className)) {{
                    row.style.display = '';
                    visibleCount++;
                }} else {{
                    row.style.display = 'none';
                }}
            }});

            currentFilter = className;

            // Mostrar indicador
            const indicator = document.getElementById('filter-indicator');
            const filterName = document.getElementById('filter-name');

            const filterLabels = {{
                'signal-buy': 'Infravaloradas (MoS ≥ 25%)',
                'signal-watchlist': 'Watchlist (10-25%)',
                'signal-fair': 'Valor Justo (±10%)',
                'signal-overvalued': 'Sobrevaloradas',
                'signal-speculative': 'Especulativas'
            }};

            filterName.textContent = filterLabels[className] || className;
            filterName.textContent += ' (' + visibleCount + ' empresas)';
            indicator.style.display = 'block';
        }}

        function clearFilter() {{
            const table = document.querySelector('tbody');
            const rows = table.querySelectorAll('tr');

            rows.forEach(row => {{
                row.style.display = '';
            }});

            currentFilter = null;
            document.getElementById('filter-indicator').style.display = 'none';
        }}
    </script>
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
