"""
Módulo para generar el PDF de tesis de inversión.
Usa matplotlib para gráficos y fpdf2 para el documento PDF.
"""

import os
import tempfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from fpdf import FPDF
from datetime import datetime


# Configuración de estilo
sns.set_style("whitegrid")
COLORS = {
    "primary": "#273A4F",
    "secondary": "#B2C3BC",
    "accent": "#0066CC",
    "positive": "#2E7D32",
    "negative": "#C62828",
    "neutral": "#757575",
}


def _sanitize(text: str) -> str:
    """Sanitize text for latin-1 encoding used by fpdf2 with core fonts."""
    if not text:
        return ""
    return text.encode('latin-1', 'replace').decode('latin-1')


class InvestmentThesisPDF(FPDF):
    """PDF personalizado para tesis de inversión."""

    def __init__(self, company_name, ticker):
        super().__init__()
        self.company_name = company_name
        self.ticker = ticker
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(117, 117, 117)
            self.cell(0, 10, f"{self.company_name} ({self.ticker}) - Investment Thesis", align="L")
            self.cell(0, 10, f"Page {self.page_no()}", align="R")
            self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(117, 117, 117)
        self.cell(0, 10, f"Generated {datetime.now().strftime('%Y-%m-%d')} | Automated Valuation System", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(39, 58, 79)  # #273A4F
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(39, 58, 79)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5, _sanitize(text))
        self.ln(3)

    def bullet_point(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.cell(5, 5, "-")
        self.multi_cell(0, 5, f" {_sanitize(text)}")


def generate_investment_pdf(ticker: str, data: dict, historical: dict,
                             scenarios: dict, news: list = None,
                             output_path: str = None) -> str:
    """
    Genera el PDF de tesis de inversión.

    Args:
        ticker: Ticker de la empresa
        data: Datos de get_company_data()
        historical: Datos de extract_historical_data()
        scenarios: Escenarios generados
        news: Lista de noticias recientes
        output_path: Path de salida

    Returns:
        Path del PDF generado
    """
    if output_path is None:
        output_path = os.path.join(ticker, f"{ticker}_tesis_inversion.pdf")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"\n📝 Generando PDF de tesis de inversión para {ticker}...")

    info = data["info"]
    company_name = info.get("longName", ticker)
    current_price = data["current_price"]
    shares = data["shares_outstanding"]

    pdf = InvestmentThesisPDF(company_name, ticker)

    # ============================================================
    # PORTADA
    # ============================================================
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(39, 58, 79)
    pdf.cell(0, 15, _sanitize(company_name), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 18)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, f"({ticker})", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(0, 102, 204)
    pdf.cell(0, 10, "Investment Thesis", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)

    # Info box
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 8, f"Current Price: ${current_price:,.2f}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Market Cap: ${info.get('marketCap', 0)/1e9:,.1f}B", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Sector: {info.get('sector', 'N/A')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Industry: {info.get('industry', 'N/A')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Date: {datetime.now().strftime('%B %d, %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")

    # ============================================================
    # DESCRIPCIÓN DEL NEGOCIO
    # ============================================================
    pdf.add_page()
    pdf.section_title("1. Business Description")

    description = info.get("longBusinessSummary", "")
    if description:
        if len(description) > 2000:
            description = description[:2000] + "..."
        pdf.body_text(description)
    else:
        pdf.body_text(f"{company_name} is a publicly traded company in the {info.get('sector', '')} sector.")

    pdf.ln(5)

    # Key metrics table
    pdf.section_title("Key Metrics")
    _add_metrics_table(pdf, info, data)

    # ============================================================
    # DATOS FINANCIEROS CLAVE
    # ============================================================
    pdf.add_page()
    pdf.section_title("2. Financial Summary (Last 3 Years)")
    _add_financial_table(pdf, historical)

    # ============================================================
    # GRÁFICOS
    # ============================================================
    pdf.add_page()
    pdf.section_title("3. Financial Charts")

    temp_dir = tempfile.mkdtemp()

    # Revenue & Net Income chart
    chart_path = _create_revenue_chart(historical, company_name, temp_dir)
    if chart_path:
        pdf.image(chart_path, x=10, w=190)
        pdf.ln(5)

    # Margins chart
    chart_path = _create_margins_chart(historical, company_name, temp_dir)
    if chart_path:
        pdf.image(chart_path, x=10, w=190)
        pdf.ln(5)

    # FCF chart
    pdf.add_page()
    chart_path = _create_fcf_chart(historical, company_name, temp_dir)
    if chart_path:
        pdf.image(chart_path, x=10, w=190)
        pdf.ln(5)

    # Price history
    if data.get("history") is not None and not data["history"].empty:
        chart_path = _create_price_chart(data["history"], company_name, ticker, temp_dir)
        if chart_path:
            pdf.image(chart_path, x=10, w=190)

    # ============================================================
    # CATALIZADORES POSITIVOS
    # ============================================================
    pdf.add_page()
    pdf.section_title("4. Positive Catalysts")
    catalysts = _generate_catalysts(info, historical, scenarios)
    for cat in catalysts:
        pdf.bullet_point(cat)
        pdf.ln(2)

    # ============================================================
    # RIESGOS
    # ============================================================
    pdf.ln(5)
    pdf.section_title("5. Key Risks")
    risks = _generate_risks(info, historical)
    for risk in risks:
        pdf.bullet_point(risk)
        pdf.ln(2)

    # ============================================================
    # VALORACIÓN
    # ============================================================
    pdf.add_page()
    pdf.section_title("6. Valuation Summary (DCF)")

    _add_valuation_summary(pdf, scenarios, data, historical)

    # Valuation chart
    chart_path = _create_valuation_chart(scenarios, data, historical, company_name, temp_dir)
    if chart_path:
        pdf.ln(5)
        pdf.image(chart_path, x=10, w=190)

    # ============================================================
    # NOTICIAS RECIENTES
    # ============================================================
    if news:
        pdf.add_page()
        pdf.section_title("7. Recent News")
        for item in news[:10]:
            title = _sanitize(item.get("title", ""))
            source = _sanitize(item.get("source", ""))
            date = item.get("date", "")
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(0, 102, 204)
            pdf.multi_cell(0, 5, title)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 4, f"{source} | {date}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

    # ============================================================
    # DISCLAIMER
    # ============================================================
    pdf.add_page()
    pdf.section_title("Disclaimer")
    pdf.body_text(
        "This report is generated automatically using publicly available data. "
        "It is intended for informational and educational purposes only and does not "
        "constitute investment advice. The projections and valuations presented are "
        "based on assumptions that may not reflect actual future performance. "
        "Always conduct your own research before making investment decisions."
    )

    pdf.output(output_path)
    print(f"  ✓ PDF guardado: {output_path}")

    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    return output_path


def _add_metrics_table(pdf, info, data):
    """Añade tabla de métricas clave."""
    metrics = [
        ("Market Cap", f"${info.get('marketCap', 0)/1e9:,.1f}B"),
        ("Enterprise Value", f"${info.get('enterpriseValue', 0)/1e9:,.1f}B"),
        ("P/E Ratio (TTM)", f"{info.get('trailingPE', 0):,.1f}x" if info.get('trailingPE') else "N/A"),
        ("Forward P/E", f"{info.get('forwardPE', 0):,.1f}x" if info.get('forwardPE') else "N/A"),
        ("EV/EBITDA", f"{info.get('enterpriseToEbitda', 0):,.1f}x" if info.get('enterpriseToEbitda') else "N/A"),
        ("Revenue Growth", f"{(info.get('revenueGrowth', 0) or 0)*100:,.1f}%"),
        ("Gross Margin", f"{(info.get('grossMargins', 0) or 0)*100:,.1f}%"),
        ("Operating Margin", f"{(info.get('operatingMargins', 0) or 0)*100:,.1f}%"),
        ("Net Margin", f"{(info.get('profitMargins', 0) or 0)*100:,.1f}%"),
        ("Beta", f"{info.get('beta', 0):,.2f}" if info.get('beta') else "N/A"),
        ("Dividend Yield", f"{(info.get('dividendYield', 0) or 0)*100:,.2f}%"),
        ("52W High", f"${info.get('fiftyTwoWeekHigh', 0):,.2f}"),
        ("52W Low", f"${info.get('fiftyTwoWeekLow', 0):,.2f}"),
    ]

    pdf.set_font("Helvetica", "", 9)
    col_width = 95

    for i in range(0, len(metrics), 2):
        pdf.set_text_color(80, 80, 80)
        pdf.cell(col_width / 2, 6, metrics[i][0], border=0)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(col_width / 2, 6, str(metrics[i][1]), border=0)

        if i + 1 < len(metrics):
            pdf.set_text_color(80, 80, 80)
            pdf.cell(col_width / 2, 6, metrics[i+1][0], border=0)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(col_width / 2, 6, str(metrics[i+1][1]), border=0)

        pdf.ln()


def _add_financial_table(pdf, historical):
    """Añade tabla resumen financiero."""
    sorted_years = sorted(historical.keys())[-3:]  # últimos 3 años

    if not sorted_years:
        pdf.body_text("No historical data available.")
        return

    # Header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(39, 58, 79)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(60, 7, "Metric ($M)", border=1, fill=True)
    for year in sorted_years:
        pdf.cell(35, 7, f"FY{year}", border=1, fill=True, align="C")
    pdf.ln()

    # Data rows
    items = [
        ("Revenue", "total_revenue"),
        ("Gross Profit", "gross_profit"),
        ("Operating Income", "operating_income"),
        ("Net Income", "net_income"),
        ("EBITDA", "ebitda"),
        ("Free Cash Flow", "free_cashflow"),
        ("Total Assets", "total_assets"),
        ("Total Debt", "total_debt"),
        ("Total Equity", "total_equity"),
    ]

    pdf.set_font("Helvetica", "", 9)
    for i, (label, key) in enumerate(items):
        if i % 2 == 0:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)

        pdf.set_text_color(50, 50, 50)
        pdf.cell(60, 6, label, border=1, fill=True)

        for year in sorted_years:
            val = historical.get(year, {}).get(key, 0)
            display = f"{val/1e6:,.0f}" if abs(val) > 1e3 else f"{val:,.0f}"
            pdf.cell(35, 6, display, border=1, fill=True, align="R")
        pdf.ln()


def _create_revenue_chart(historical, company_name, temp_dir):
    """Crea gráfico de Revenue y Net Income."""
    sorted_years = sorted(historical.keys())
    if len(sorted_years) < 2:
        return None

    revenues = [historical[y].get("total_revenue", 0) / 1e9 for y in sorted_years]
    net_income = [historical[y].get("net_income", 0) / 1e9 for y in sorted_years]

    fig, ax1 = plt.subplots(figsize=(10, 5))

    x = np.arange(len(sorted_years))
    width = 0.35

    bars1 = ax1.bar(x - width/2, revenues, width, label='Revenue', color=COLORS["primary"], alpha=0.85)
    bars2 = ax1.bar(x + width/2, net_income, width, label='Net Income', color=COLORS["secondary"], alpha=0.85)

    ax1.set_xlabel('Year')
    ax1.set_ylabel('$B')
    ax1.set_title(f'{company_name} - Revenue & Net Income ($B)')
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(y) for y in sorted_years])
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(temp_dir, "revenue_chart.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


def _create_margins_chart(historical, company_name, temp_dir):
    """Crea gráfico de márgenes."""
    sorted_years = sorted(historical.keys())
    if len(sorted_years) < 2:
        return None

    gross_m = []
    ebitda_m = []
    net_m = []

    for y in sorted_years:
        rev = historical[y].get("total_revenue", 0)
        if rev > 0:
            gross_m.append(historical[y].get("gross_profit", 0) / rev * 100)
            ebitda_m.append(historical[y].get("ebitda", 0) / rev * 100)
            net_m.append(historical[y].get("net_income", 0) / rev * 100)
        else:
            gross_m.append(0)
            ebitda_m.append(0)
            net_m.append(0)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(sorted_years, gross_m, 'o-', label='Gross Margin', color=COLORS["primary"], linewidth=2)
    ax.plot(sorted_years, ebitda_m, 's-', label='EBITDA Margin', color=COLORS["accent"], linewidth=2)
    ax.plot(sorted_years, net_m, '^-', label='Net Margin', color=COLORS["positive"], linewidth=2)

    ax.set_xlabel('Year')
    ax.set_ylabel('Margin (%)')
    ax.set_title(f'{company_name} - Margin Evolution')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())

    plt.tight_layout()
    path = os.path.join(temp_dir, "margins_chart.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


def _create_fcf_chart(historical, company_name, temp_dir):
    """Crea gráfico de Free Cash Flow."""
    sorted_years = sorted(historical.keys())
    if len(sorted_years) < 2:
        return None

    fcf = [historical[y].get("free_cashflow", 0) / 1e9 for y in sorted_years]
    ocf = [historical[y].get("operating_cashflow", 0) / 1e9 for y in sorted_years]
    capex = [abs(historical[y].get("capex", 0)) / 1e9 for y in sorted_years]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(sorted_years))
    width = 0.25

    ax.bar(x - width, ocf, width, label='Operating CF', color=COLORS["primary"], alpha=0.85)
    ax.bar(x, [-c for c in capex], width, label='CapEx', color=COLORS["negative"], alpha=0.7)
    ax.bar(x + width, fcf, width, label='Free Cash Flow', color=COLORS["positive"], alpha=0.85)

    ax.set_xlabel('Year')
    ax.set_ylabel('$B')
    ax.set_title(f'{company_name} - Cash Flow Analysis ($B)')
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in sorted_years])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=0, color='black', linewidth=0.5)

    plt.tight_layout()
    path = os.path.join(temp_dir, "fcf_chart.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


def _create_price_chart(history, company_name, ticker, temp_dir):
    """Crea gráfico de precio histórico."""
    fig, ax = plt.subplots(figsize=(10, 5))

    # yahooquery usa "close" (lowercase), yfinance usa "Close"
    close_col = "Close" if "Close" in history.columns else "close" if "close" in history.columns else None
    if close_col is None:
        plt.close()
        return None

    ax.plot(history.index, history[close_col], color=COLORS["primary"], linewidth=1.5)
    ax.fill_between(history.index, history[close_col], alpha=0.1, color=COLORS["primary"])

    ax.set_xlabel('Date')
    ax.set_ylabel('Price ($)')
    ax.set_title(f'{company_name} ({ticker}) - Stock Price (5Y)')
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(temp_dir, "price_chart.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


def _create_valuation_chart(scenarios, data, historical, company_name, temp_dir):
    """Crea gráfico comparando precio actual vs valoración por escenario."""
    current_price = data["current_price"]
    base_sc = scenarios["base"]
    bull_sc = scenarios["bull"]
    bear_sc = scenarios["bear"]

    # Calculate approximate intrinsic values from scenarios
    sorted_years = sorted(historical.keys())
    if not sorted_years:
        return None

    last_rev = historical[sorted_years[-1]].get("total_revenue", 0)
    shares = data["shares_outstanding"]
    if shares == 0 or last_rev == 0:
        return None

    values = {}
    for name, sc in [("Bear", bear_sc), ("Base", base_sc), ("Bull", bull_sc)]:
        # Simplified DCF approximation for the chart
        rev = last_rev
        total_pv = 0
        for i in range(1, 6):
            rev *= (1 + sc[f"revenue_growth_y{i}"])
            ebitda = rev * sc["gross_margin"] * (1 - sc["sga_pct"] / sc["gross_margin"])
            fcf = ebitda * (1 - sc["tax_rate"]) * (1 - sc["capex_pct"] / max(sc["gross_margin"], 0.01))
            pv = fcf / (1 + sc["wacc"]) ** i
            total_pv += pv

        # Terminal value
        tv = fcf * sc["terminal_multiple"] / (1 + sc["wacc"]) ** 5
        ev = (total_pv + tv) / 1e6  # in millions

        # Net debt
        cash = historical[sorted_years[-1]].get("cash", 0)
        debt = historical[sorted_years[-1]].get("total_debt", 0)
        net_debt = debt - cash

        equity = (ev * 1e6 - net_debt)  # back to absolute
        per_share = equity / shares if shares > 0 else 0
        values[name] = per_share

    fig, ax = plt.subplots(figsize=(10, 5))

    labels = list(values.keys()) + ["Current Price"]
    vals = list(values.values()) + [current_price]
    colors_list = [COLORS["negative"], COLORS["accent"], COLORS["positive"], COLORS["neutral"]]

    bars = ax.bar(labels, vals, color=colors_list, alpha=0.85, edgecolor='white', linewidth=2)

    ax.axhline(y=current_price, color=COLORS["neutral"], linestyle='--', linewidth=1.5, label='Current Price')

    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + max(vals)*0.02,
                f'${val:,.0f}', ha='center', va='bottom', fontweight='bold')

    ax.set_ylabel('Price per Share ($)')
    ax.set_title(f'{company_name} - Valuation Scenarios vs Current Price')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(temp_dir, "valuation_chart.png")
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    return path


def _generate_catalysts(info, historical, scenarios):
    """Genera catalizadores positivos automáticamente."""
    catalysts = []
    sector = info.get("sector", "")
    industry = info.get("industry", "")
    growth = info.get("revenueGrowth", 0) or 0
    margin = info.get("grossMargins", 0) or 0

    if growth > 0.10:
        catalysts.append(f"Strong revenue growth of {growth*100:.1f}% indicates robust demand and market expansion potential.")
    elif growth > 0:
        catalysts.append(f"Positive revenue growth of {growth*100:.1f}% shows continued business momentum.")

    if margin > 0.50:
        catalysts.append(f"High gross margin of {margin*100:.1f}% demonstrates strong pricing power and competitive moat.")

    operating_margin = info.get("operatingMargins", 0) or 0
    if operating_margin > 0.20:
        catalysts.append(f"Operating margin of {operating_margin*100:.1f}% shows operational efficiency and scale benefits.")

    # FCF generation
    sorted_years = sorted(historical.keys())
    if sorted_years:
        last_fcf = historical[sorted_years[-1]].get("free_cashflow", 0)
        if last_fcf > 0:
            catalysts.append(f"Strong free cash flow generation of ${last_fcf/1e9:.1f}B provides flexibility for buybacks, dividends, or M&A.")

    # Market position
    market_cap = info.get("marketCap", 0)
    if market_cap > 100e9:
        catalysts.append(f"Large-cap status with ${market_cap/1e9:.0f}B market cap provides stability and institutional investor interest.")

    # Analyst targets
    target = info.get("targetMeanPrice", 0)
    current = info.get("currentPrice") or info.get("regularMarketPrice", 0)
    if target and current and target > current:
        upside = (target / current - 1) * 100
        catalysts.append(f"Analyst consensus price target implies {upside:.0f}% upside from current levels.")

    if not catalysts:
        catalysts.append(f"Operating in the {industry} industry within {sector} sector with potential for growth.")
        catalysts.append("Publicly traded with access to capital markets for growth initiatives.")

    return catalysts


def _generate_risks(info, historical):
    """Genera riesgos automáticamente."""
    risks = []
    sector = info.get("sector", "")
    beta = info.get("beta", 1.0) or 1.0
    debt_equity = info.get("debtToEquity", 0) or 0
    pe = info.get("trailingPE", 0) or 0

    if beta > 1.3:
        risks.append(f"Higher-than-average volatility (beta: {beta:.2f}) exposes shareholders to amplified market movements.")

    if debt_equity > 100:
        risks.append(f"Elevated debt-to-equity ratio of {debt_equity:.0f}% increases financial risk and interest rate sensitivity.")

    if pe > 30:
        risks.append(f"High P/E ratio of {pe:.1f}x suggests premium valuation that may compress under market stress.")

    growth = info.get("revenueGrowth", 0) or 0
    if growth < 0:
        risks.append(f"Declining revenue ({growth*100:.1f}% growth) signals potential market share loss or industry headwinds.")

    risks.append("Macroeconomic risks including recession, inflation, and interest rate changes could impact performance.")
    risks.append(f"Competitive pressures in the {info.get('industry', 'industry')} space may erode margins or market share.")

    # Regulatory
    if sector in ["Technology", "Communication Services", "Healthcare", "Financial Services"]:
        risks.append(f"Regulatory scrutiny in the {sector} sector could lead to compliance costs or operational restrictions.")

    return risks


def _add_valuation_summary(pdf, scenarios, data, historical):
    """Añade resumen de valoración al PDF."""
    current_price = data["current_price"]

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.body_text(f"Current Price: ${current_price:,.2f}")
    pdf.ln(3)

    # Table header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(39, 58, 79)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 7, "Scenario", border=1, fill=True, align="C")
    pdf.cell(30, 7, "Rev Growth Y1", border=1, fill=True, align="C")
    pdf.cell(25, 7, "WACC", border=1, fill=True, align="C")
    pdf.cell(25, 7, "TV Multiple", border=1, fill=True, align="C")
    pdf.cell(35, 7, "Gross Margin", border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for name, sc in [("Bear Case", scenarios["bear"]), ("Base Case", scenarios["base"]), ("Bull Case", scenarios["bull"])]:
        if "Bull" in name:
            pdf.set_fill_color(232, 245, 233)
        elif "Bear" in name:
            pdf.set_fill_color(255, 235, 238)
        else:
            pdf.set_fill_color(245, 245, 245)

        pdf.set_text_color(50, 50, 50)
        pdf.cell(40, 6, name, border=1, fill=True)
        pdf.cell(30, 6, f"{sc['revenue_growth_y1']*100:.1f}%", border=1, fill=True, align="C")
        pdf.cell(25, 6, f"{sc['wacc']*100:.1f}%", border=1, fill=True, align="C")
        pdf.cell(25, 6, f"{sc['terminal_multiple']:.0f}x", border=1, fill=True, align="C")
        pdf.cell(35, 6, f"{sc['gross_margin']*100:.1f}%", border=1, fill=True, align="C")
        pdf.ln()

    pdf.ln(5)
    pdf.body_text("Note: Detailed DCF calculations are available in the accompanying Excel model. "
                  "The Excel model includes a sensitivity analysis table showing equity value per share "
                  "across different WACC and Terminal Value Multiple assumptions.")


if __name__ == "__main__":
    print("Este módulo se usa desde valorar_empresa.py")
