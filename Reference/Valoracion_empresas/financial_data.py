"""
Módulo para obtener datos financieros usando yahooquery (principal) y SEC XBRL.
Proporciona: Income Statement, Balance Sheet, Cash Flow, info de empresa,
segmentos de negocio, y estimaciones de analistas.
"""

import re
import time
import requests
import numpy as np
import pandas as pd
from yahooquery import Ticker


HEADERS = {
    "User-Agent": "ValoracionEmpresas/1.0 (contacto@valoracion.com)",
}


def get_company_data(ticker: str) -> dict:
    """
    Obtiene todos los datos financieros necesarios para la valoración.

    Returns dict con:
        - info: datos generales de la empresa
        - income_stmt: Income Statement (DataFrames con columnas por métrica)
        - balance_sheet: Balance Sheet
        - cash_flow: Cash Flow Statement
        - segments: segmentos de negocio con revenues
        - estimates: estimaciones de analistas
        - current_price: precio actual
        - shares_outstanding: acciones en circulación
        - history: precio histórico
    """
    print(f"\n📊 Obteniendo datos financieros para {ticker}...")

    stock = Ticker(ticker)

    # Info general - combinar varias fuentes de yahooquery
    price_data = stock.price.get(ticker, {})
    fin_data = stock.financial_data.get(ticker, {})
    profile = stock.summary_profile.get(ticker, {})
    key_stats = stock.key_stats.get(ticker, {})
    summary = stock.summary_detail.get(ticker, {})

    # Construir dict de info compatible con el formato anterior
    info = _build_info_dict(price_data, fin_data, profile, key_stats, summary, ticker)
    print(f"  Empresa: {info.get('longName', ticker)}")
    print(f"  Sector: {info.get('sector', 'N/A')}")
    print(f"  Industria: {info.get('industry', 'N/A')}")

    # Estados financieros anuales
    income_stmt_raw = stock.income_statement(frequency='a')
    balance_sheet_raw = stock.balance_sheet(frequency='a')
    cash_flow_raw = stock.cash_flow(frequency='a')

    # Convertir a formato pivotado (años como columnas, métricas como filas)
    income_stmt = _pivot_financial_df(income_stmt_raw, ticker)
    balance_sheet = _pivot_financial_df(balance_sheet_raw, ticker)
    cash_flow = _pivot_financial_df(cash_flow_raw, ticker)

    print(f"  Income Statement: {len(income_stmt.columns)} periodos")
    print(f"  Balance Sheet: {len(balance_sheet.columns)} periodos")
    print(f"  Cash Flow: {len(cash_flow.columns)} periodos")

    # Precio actual y acciones
    current_price = fin_data.get("currentPrice", 0) or price_data.get("regularMarketPrice", 0)
    shares_outstanding = key_stats.get("sharesOutstanding", 0) or key_stats.get("impliedSharesOutstanding", 0) or 0

    # Estimaciones de analistas
    estimates = _get_analyst_estimates(info, fin_data)

    # Segmentos de negocio
    segments = _get_business_segments(ticker, info, income_stmt)

    # Datos históricos para gráficos
    try:
        hist = stock.history(period="5y", interval="1mo")
        if isinstance(hist, dict):
            hist = pd.DataFrame()
        elif isinstance(hist, pd.DataFrame) and hist.empty:
            hist = pd.DataFrame()
        else:
            # yahooquery returns multi-index with ticker, flatten it
            if isinstance(hist.index, pd.MultiIndex):
                hist = hist.reset_index(level=0, drop=True)
    except Exception:
        hist = pd.DataFrame()

    result = {
        "info": info,
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "segments": segments,
        "estimates": estimates,
        "current_price": current_price,
        "shares_outstanding": shares_outstanding,
        "history": hist,
    }

    return result


def _build_info_dict(price_data, fin_data, profile, key_stats, summary, ticker):
    """Construye un dict de info unificado desde yahooquery."""
    info = {}

    # Desde price_data
    if isinstance(price_data, dict):
        info["longName"] = price_data.get("longName") or price_data.get("shortName", ticker)
        info["regularMarketPrice"] = price_data.get("regularMarketPrice", 0)
        info["marketCap"] = price_data.get("marketCap", 0)
        info["currency"] = price_data.get("currency", "USD")

    # Desde profile
    if isinstance(profile, dict):
        info["sector"] = profile.get("sector", "")
        info["industry"] = profile.get("industry", "")
        info["longBusinessSummary"] = profile.get("longBusinessSummary", "")
        info["country"] = profile.get("country", "")

    # Desde financial_data
    if isinstance(fin_data, dict):
        info["currentPrice"] = fin_data.get("currentPrice", 0)
        info["targetHighPrice"] = fin_data.get("targetHighPrice", 0)
        info["targetLowPrice"] = fin_data.get("targetLowPrice", 0)
        info["targetMeanPrice"] = fin_data.get("targetMeanPrice", 0)
        info["totalRevenue"] = fin_data.get("totalRevenue", 0)
        info["revenueGrowth"] = fin_data.get("revenueGrowth", 0)
        info["grossMargins"] = fin_data.get("grossMargins", 0)
        info["operatingMargins"] = fin_data.get("operatingMargins", 0)
        info["profitMargins"] = fin_data.get("profitMargins", 0)
        info["totalCash"] = fin_data.get("totalCash", 0)
        info["totalDebt"] = fin_data.get("totalDebt", 0)
        info["enterpriseValue"] = key_stats.get("enterpriseValue", 0) if isinstance(key_stats, dict) else 0

    # Desde key_stats
    if isinstance(key_stats, dict):
        info["beta"] = key_stats.get("beta", 1.0)
        info["sharesOutstanding"] = key_stats.get("sharesOutstanding", 0)
        info["forwardPE"] = key_stats.get("forwardPE", 0)
        info["enterpriseToEbitda"] = key_stats.get("enterpriseToEbitda", 0)

    # Desde summary_detail
    if isinstance(summary, dict):
        info["trailingPE"] = summary.get("trailingPE", 0)
        info["dividendYield"] = summary.get("dividendYield", 0)
        info["fiftyTwoWeekHigh"] = summary.get("fiftyTwoWeekHigh", 0)
        info["fiftyTwoWeekLow"] = summary.get("fiftyTwoWeekLow", 0)

    return info


def _pivot_financial_df(df, ticker):
    """
    Convierte DataFrame de yahooquery (filas=periodos, cols=métricas)
    a formato pivotado (filas=métricas, cols=fechas) compatible con yfinance.
    """
    if df is None or (isinstance(df, str) and "error" in df.lower()):
        return pd.DataFrame()

    if isinstance(df, pd.DataFrame) and not df.empty:
        # Filter to this ticker if multi-index
        if 'symbol' in df.columns:
            df = df[df['symbol'] == ticker].copy()
        elif isinstance(df.index, pd.MultiIndex):
            try:
                df = df.loc[ticker].copy()
            except KeyError:
                return pd.DataFrame()

        if 'asOfDate' not in df.columns:
            return pd.DataFrame()

        # Keep only annual data
        if 'periodType' in df.columns:
            df = df[df['periodType'] == '12M'].copy()
            if df.empty:
                # Try TTM or any available
                df = pd.DataFrame()
                return df

        # Set date as index and transpose
        df = df.set_index('asOfDate')
        # Drop non-numeric columns
        drop_cols = ['periodType', 'currencyCode', 'symbol']
        df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')

        # Transpose: metrics become rows, dates become columns
        df = df.T
        # Ensure column dates are datetime
        df.columns = pd.to_datetime(df.columns)
        # Sort columns by date
        df = df[sorted(df.columns)]

        return df

    return pd.DataFrame()


def _get_analyst_estimates(info: dict, fin_data: dict) -> dict:
    """Obtiene estimaciones de analistas."""
    estimates = {
        "revenue_growth": {},
        "eps": {},
        "margins": {},
        "target_prices": {},
    }

    growth = info.get("revenueGrowth", 0) or 0
    estimates["revenue_growth"]["current"] = growth

    estimates["target_prices"] = {
        "high": info.get("targetHighPrice", 0) or 0,
        "low": info.get("targetLowPrice", 0) or 0,
        "mean": info.get("targetMeanPrice", 0) or 0,
        "current": info.get("currentPrice", 0) or 0,
    }

    return estimates


def _get_business_segments(ticker: str, info: dict, income_stmt) -> list:
    """
    Intenta obtener segmentos de negocio desde SEC XBRL (solo EEUU).
    Si no lo consigue, genera segmentos basados en la info disponible.
    """
    segments = []
    if "." not in ticker:
        segments = _try_sec_segments(ticker)

    if segments:
        print(f"  Segmentos encontrados (SEC): {len(segments)}")
        return segments

    segments = _generate_fallback_segments(info, income_stmt)
    print(f"  Segmentos generados (fallback): {len(segments)}")
    return segments


def _try_sec_segments(ticker: str) -> list:
    """Intenta obtener segmentos de SEC EDGAR XBRL."""
    try:
        tickers_url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(tickers_url, headers=HEADERS, timeout=15)
        data = resp.json()

        cik = None
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                cik = str(entry["cik_str"]).zfill(10)
                break

        if not cik:
            return []

        facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        resp = requests.get(facts_url, headers=HEADERS, timeout=30)

        if resp.status_code != 200:
            return []

        facts = resp.json()
        us_gaap = facts.get("facts", {}).get("us-gaap", {})

        segment_data = {}
        revenue_keys = [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "Revenue",
            "SalesRevenueNet",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
        ]

        for key in revenue_keys:
            if key in us_gaap:
                units = us_gaap[key].get("units", {}).get("USD", [])
                for entry in units:
                    segment = entry.get("segment")
                    if segment and entry.get("form") == "10-K":
                        seg_label = segment.get("value", "")
                        if seg_label and ":" in seg_label:
                            seg_label = seg_label.split(":")[-1]

                        fiscal_year = entry.get("fy")
                        val = entry.get("val", 0)

                        if seg_label not in segment_data:
                            segment_data[seg_label] = {}
                        segment_data[seg_label][fiscal_year] = val

                if segment_data:
                    break

        if not segment_data:
            return []

        segments = []
        for name, years_data in segment_data.items():
            clean_name = name.replace("Member", "").replace("Segment", "")
            clean_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', clean_name).strip()

            if clean_name and years_data:
                segments.append({
                    "name": clean_name,
                    "revenues": years_data,
                })

        return segments

    except Exception as e:
        print(f"  ⚠ Error obteniendo segmentos de SEC: {e}")
        return []


def _generate_fallback_segments(info: dict, income_stmt) -> list:
    """Genera segmentos fallback basados en info disponible."""
    sector = info.get("sector", "")
    industry = info.get("industry", "")

    total_revenues = {}
    if income_stmt is not None and not income_stmt.empty:
        for col in income_stmt.columns:
            year = col.year
            rev = _safe_get(income_stmt, "TotalRevenue", col)
            if not rev:
                rev = _safe_get(income_stmt, "Total Revenue", col)
            if rev and not np.isnan(rev):
                total_revenues[year] = float(rev)

    segments = [
        {
            "name": f"{industry or sector or 'Principal'}",
            "revenues": total_revenues,
            "pct": 1.0,
        }
    ]

    return segments


def extract_historical_data(data: dict) -> dict:
    """
    Extrae datos históricos formateados para el modelo de valoración.
    Retorna dict con años como keys y métricas financieras.
    """
    income = data["income_stmt"]
    balance = data["balance_sheet"]
    cashflow = data["cash_flow"]

    years_data = {}

    # Mapping de nombres yahooquery -> nuestras keys
    # yahooquery usa CamelCase sin espacios
    if income is not None and not income.empty:
        for col in income.columns:
            year = col.year
            yr = {}

            yr["total_revenue"] = _safe_get_multi(income, ["TotalRevenue", "Total Revenue"], col)
            yr["cost_of_revenue"] = _safe_get_multi(income, ["CostOfRevenue", "Cost Of Revenue"], col)
            yr["gross_profit"] = _safe_get_multi(income, ["GrossProfit", "Gross Profit"], col)
            yr["operating_expense"] = _safe_get_multi(income, ["OperatingExpense", "Operating Expense"], col)
            yr["operating_income"] = _safe_get_multi(income, ["OperatingIncome", "Operating Income", "EBIT"], col)
            yr["ebitda"] = _safe_get_multi(income, ["EBITDA", "NormalizedEBITDA"], col)
            yr["net_income"] = _safe_get_multi(income, ["NetIncome", "Net Income", "NetIncomeCommonStockholders"], col)
            yr["interest_expense"] = _safe_get_multi(income, ["InterestExpense", "Interest Expense", "InterestExpenseNonOperating"], col)
            yr["tax_provision"] = _safe_get_multi(income, ["TaxProvision", "Tax Provision", "IncomeTaxExpense"], col)
            yr["diluted_eps"] = _safe_get_multi(income, ["DilutedEPS", "Diluted EPS", "BasicEPS"], col)
            yr["research_development"] = _safe_get_multi(income, ["ResearchAndDevelopment", "Research And Development"], col)
            yr["selling_general_admin"] = _safe_get_multi(income, ["SellingGeneralAndAdministration", "Selling General And Administration", "SellingAndMarketingExpense"], col)
            yr["depreciation"] = _safe_get_multi(income, ["ReconciledDepreciation", "DepreciationAndAmortizationInIncomeStatement", "DepreciationAmortizationDepletionIncomeStatement"], col)

            # Si no hay gross_profit pero sí revenue y COGS, calcular
            if not yr["gross_profit"] and yr["total_revenue"] and yr["cost_of_revenue"]:
                yr["gross_profit"] = yr["total_revenue"] - abs(yr["cost_of_revenue"])

            # Si no hay EBITDA, intentar calcularlo
            if not yr["ebitda"] and yr["operating_income"] and yr["depreciation"]:
                yr["ebitda"] = yr["operating_income"] + abs(yr["depreciation"])

            years_data[year] = yr

    # Balance Sheet
    if balance is not None and not balance.empty:
        for col in balance.columns:
            year = col.year
            if year not in years_data:
                years_data[year] = {}

            yr = years_data[year]
            yr["total_assets"] = _safe_get_multi(balance, ["TotalAssets", "Total Assets"], col)
            yr["total_liabilities"] = _safe_get_multi(balance, ["TotalLiabilitiesNetMinorityInterest", "Total Liabilities Net Minority Interest", "TotalNonCurrentLiabilitiesNetMinorityInterest"], col)
            yr["total_equity"] = _safe_get_multi(balance, ["TotalEquityGrossMinorityInterest", "StockholdersEquity", "CommonStockEquity"], col)
            yr["cash"] = _safe_get_multi(balance, ["CashAndCashEquivalents", "Cash And Cash Equivalents", "CashCashEquivalentsAndShortTermInvestments", "CashFinancial"], col)
            yr["total_debt"] = _safe_get_multi(balance, ["TotalDebt", "Total Debt", "LongTermDebt"], col)
            yr["current_assets"] = _safe_get_multi(balance, ["CurrentAssets", "Current Assets"], col)
            yr["current_liabilities"] = _safe_get_multi(balance, ["CurrentLiabilities", "Current Liabilities"], col)
            yr["net_ppe"] = _safe_get_multi(balance, ["NetPPE", "Net PPE", "GrossPPE"], col)
            yr["goodwill"] = _safe_get_multi(balance, ["Goodwill"], col)
            yr["intangible_assets"] = _safe_get_multi(balance, ["IntangibleAssets", "OtherIntangibleAssets", "GoodwillAndOtherIntangibleAssets"], col)

    # Cash Flow
    if cashflow is not None and not cashflow.empty:
        for col in cashflow.columns:
            year = col.year
            if year not in years_data:
                years_data[year] = {}

            yr = years_data[year]
            yr["operating_cashflow"] = _safe_get_multi(cashflow, ["OperatingCashFlow", "Operating Cash Flow", "CashFlowsfromusedinOperatingActivitiesDirect"], col)
            yr["capex"] = _safe_get_multi(cashflow, ["CapitalExpenditure", "Capital Expenditure"], col)
            yr["free_cashflow"] = _safe_get_multi(cashflow, ["FreeCashFlow", "Free Cash Flow"], col)
            yr["depreciation_cf"] = _safe_get_multi(cashflow, ["DepreciationAndAmortization", "Depreciation And Amortization"], col)
            yr["stock_based_comp"] = _safe_get_multi(cashflow, ["StockBasedCompensation", "Stock Based Compensation"], col)
            yr["change_working_capital"] = _safe_get_multi(cashflow, ["ChangeInWorkingCapital", "Change In Working Capital"], col)

            # Si no hay FCF, calcularlo
            if not yr.get("free_cashflow") and yr.get("operating_cashflow") and yr.get("capex"):
                yr["free_cashflow"] = yr["operating_cashflow"] + yr["capex"]  # capex ya es negativo

    # Filtrar años sin revenue (datos incompletos)
    years_data = {y: d for y, d in years_data.items() if d.get("total_revenue", 0) != 0}

    return years_data


def generate_scenarios(data: dict, historical: dict) -> dict:
    """
    Genera los 3 escenarios (Base, Bull, Bear) basándose en datos históricos
    y estimaciones de analistas.
    """
    info = data["info"]
    estimates = data["estimates"]
    segments = data["segments"]

    # Calcular tasas de crecimiento históricas
    sorted_years = sorted(historical.keys())
    revenue_growths = []
    for i in range(1, len(sorted_years)):
        prev_rev = historical[sorted_years[i-1]].get("total_revenue", 0)
        curr_rev = historical[sorted_years[i]].get("total_revenue", 0)
        if prev_rev and curr_rev and prev_rev > 0:
            revenue_growths.append(curr_rev / prev_rev - 1)

    avg_growth = np.mean(revenue_growths) if revenue_growths else 0.05

    # Márgenes históricos promedio
    margins = _calculate_avg_margins(historical, sorted_years)

    # Usar estimaciones de analistas si están disponibles
    analyst_growth = estimates.get("revenue_growth", {}).get("current", None)
    if analyst_growth and analyst_growth != 0:
        base_growth = analyst_growth
    else:
        base_growth = avg_growth

    # Limitar crecimiento a rangos razonables
    base_growth = max(min(base_growth, 0.40), -0.15)

    # Para bull/bear: usar offsets absolutos en vez de multiplicadores
    # Esto funciona correctamente tanto para growth positivo como negativo
    bull_premium = max(abs(base_growth) * 0.3, 0.03)  # al menos +3%
    bear_discount = max(abs(base_growth) * 0.3, 0.03)  # al menos -3%

    # Generar escenarios
    scenarios = {
        "base": {
            "name": "Base Case",
            "revenue_growth_y1": base_growth,
            "revenue_growth_y2": base_growth * 0.9 if base_growth > 0 else base_growth + 0.02,
            "revenue_growth_y3": base_growth * 0.8 if base_growth > 0 else base_growth + 0.03,
            "revenue_growth_y4": base_growth * 0.7 if base_growth > 0 else base_growth + 0.04,
            "revenue_growth_y5": base_growth * 0.6 if base_growth > 0 else base_growth + 0.05,
            "gross_margin": margins["gross_margin"],
            "sga_pct": margins["sga_pct"],
            "rd_pct": margins["rd_pct"],
            "da_pct": margins["da_pct"],
            "capex_pct": margins["capex_pct"],
            "tax_rate": margins["tax_rate"],
            "wacc": _estimate_wacc(info),
            "terminal_multiple": _estimate_terminal_multiple(info),
        },
        "bull": {
            "name": "Bull Case",
            "revenue_growth_y1": base_growth + bull_premium,
            "revenue_growth_y2": base_growth + bull_premium * 0.9,
            "revenue_growth_y3": base_growth + bull_premium * 0.8,
            "revenue_growth_y4": base_growth + bull_premium * 0.7,
            "revenue_growth_y5": base_growth + bull_premium * 0.6,
            "gross_margin": min(margins["gross_margin"] + 0.02, 0.95),
            "sga_pct": max(margins["sga_pct"] - 0.01, 0.01),
            "rd_pct": margins["rd_pct"],
            "da_pct": margins["da_pct"],
            "capex_pct": margins["capex_pct"],
            "tax_rate": margins["tax_rate"],
            "wacc": _estimate_wacc(info) - 0.01,
            "terminal_multiple": _estimate_terminal_multiple(info) + 2,
        },
        "bear": {
            "name": "Bear Case",
            "revenue_growth_y1": base_growth - bear_discount,
            "revenue_growth_y2": base_growth - bear_discount * 0.9,
            "revenue_growth_y3": base_growth - bear_discount * 0.8,
            "revenue_growth_y4": base_growth - bear_discount * 0.7,
            "revenue_growth_y5": base_growth - bear_discount * 0.6,
            "gross_margin": max(margins["gross_margin"] - 0.02, 0.1),
            "sga_pct": margins["sga_pct"] + 0.01,
            "rd_pct": margins["rd_pct"] + 0.005,
            "da_pct": margins["da_pct"],
            "capex_pct": margins["capex_pct"] * 1.1,
            "tax_rate": margins["tax_rate"],
            "wacc": _estimate_wacc(info) + 0.02,
            "terminal_multiple": max(_estimate_terminal_multiple(info) - 3, 5),
        },
    }

    # Añadir crecimiento por segmento
    for scenario_key, scenario in scenarios.items():
        segment_growths = []
        for seg in segments:
            seg_growth = []
            for y in range(1, 6):
                g = scenario[f"revenue_growth_y{y}"]
                seg_growth.append(g)
            segment_growths.append({
                "name": seg["name"],
                "growth_rates": seg_growth,
            })
        scenario["segments"] = segment_growths

    return scenarios


def _calculate_avg_margins(historical: dict, sorted_years: list) -> dict:
    """Calcula márgenes promedio de los últimos años disponibles."""
    gross_margins = []
    sga_pcts = []
    rd_pcts = []
    da_pcts = []
    capex_pcts = []
    tax_rates = []

    for year in sorted_years:
        yr = historical[year]
        rev = yr.get("total_revenue", 0)
        if not rev or rev == 0:
            continue

        gp = yr.get("gross_profit", 0)
        if gp:
            gross_margins.append(gp / rev)

        sga = yr.get("selling_general_admin", 0)
        if sga:
            sga_pcts.append(abs(sga) / rev)

        rd = yr.get("research_development", 0)
        if rd:
            rd_pcts.append(abs(rd) / rev)

        da = yr.get("depreciation", 0) or yr.get("depreciation_cf", 0)
        if da:
            da_pcts.append(abs(da) / rev)

        capex = yr.get("capex", 0)
        if capex:
            capex_pcts.append(abs(capex) / rev)

        tax = yr.get("tax_provision", 0)
        ebt = yr.get("operating_income", 0)
        if tax and ebt and ebt > 0:
            tax_rates.append(abs(tax) / ebt)

    return {
        "gross_margin": np.mean(gross_margins) if gross_margins else 0.40,
        "sga_pct": np.mean(sga_pcts) if sga_pcts else 0.15,
        "rd_pct": np.mean(rd_pcts) if rd_pcts else 0.05,
        "da_pct": np.mean(da_pcts) if da_pcts else 0.03,
        "capex_pct": np.mean(capex_pcts) if capex_pcts else 0.04,
        "tax_rate": min(np.mean(tax_rates), 0.35) if tax_rates else 0.21,
    }


def _estimate_wacc(info: dict) -> float:
    """Estima WACC basado en beta y sector."""
    beta = info.get("beta", 1.0)
    if not beta or beta == 0:
        beta = 1.0

    rf = 0.045
    erp = 0.055
    ke = rf + abs(beta) * erp

    kd = 0.05
    market_cap = info.get("marketCap", 0) or 0
    total_debt = info.get("totalDebt", 0) or 0
    tax_rate = 0.21

    if market_cap > 0:
        equity_weight = market_cap / (market_cap + total_debt)
        debt_weight = 1 - equity_weight
    else:
        equity_weight = 0.8
        debt_weight = 0.2

    wacc = ke * equity_weight + kd * (1 - tax_rate) * debt_weight
    return round(max(wacc, 0.05), 4)


def _estimate_terminal_multiple(info: dict) -> float:
    """Estima el múltiplo terminal basado en sector y crecimiento."""
    sector = info.get("sector", "")
    growth = info.get("revenueGrowth", 0) or 0

    sector_multiples = {
        "Technology": 18,
        "Communication Services": 14,
        "Consumer Cyclical": 12,
        "Consumer Defensive": 11,
        "Healthcare": 15,
        "Financial Services": 10,
        "Industrials": 11,
        "Energy": 8,
        "Utilities": 9,
        "Real Estate": 12,
        "Basic Materials": 9,
    }

    base_multiple = sector_multiples.get(sector, 12)

    if growth > 0.20:
        base_multiple += 3
    elif growth > 0.10:
        base_multiple += 1
    elif growth < 0:
        base_multiple -= 2

    return max(base_multiple, 5)


def _safe_get(df, key, col):
    """Obtiene un valor de un DataFrame de forma segura."""
    try:
        if key in df.index:
            val = df.loc[key, col]
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                return float(val)
    except Exception:
        pass
    return 0


def _safe_get_multi(df, keys, col):
    """Intenta múltiples keys para obtener un valor."""
    for key in keys:
        val = _safe_get(df, key, col)
        if val != 0:
            return val
    return 0


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    data = get_company_data(ticker)
    historical = extract_historical_data(data)
    scenarios = generate_scenarios(data, historical)

    print(f"\n--- Resumen para {ticker} ---")
    print(f"Precio: {data['current_price']}")
    print(f"Acciones: {data['shares_outstanding']:,.0f}")
    print(f"Segmentos: {[s['name'] for s in data['segments']]}")

    sorted_years = sorted(historical.keys())
    for y in sorted_years:
        rev = historical[y].get('total_revenue', 0)
        ni = historical[y].get('net_income', 0)
        print(f"  FY{y}: Rev={rev/1e6:,.0f}M, NI={ni/1e6:,.0f}M")

    for k, v in scenarios.items():
        print(f"\nEscenario {k}: Growth Y1={v['revenue_growth_y1']:.1%}, WACC={v['wacc']:.1%}, TV={v['terminal_multiple']}x")
