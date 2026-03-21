"""
Datos financieros via yahooquery (principal) + SEC XBRL para segmentos.
Proporciona: Income Statement, Balance Sheet, Cash Flow, info de empresa,
segmentos de negocio, y estimaciones de analistas.

Funciones principales:
    get_company_data(ticker) -> dict con todos los datos crudos
    extract_historical_data(data) -> dict {year: {metrics}}
    generate_scenarios(data, historical) -> dict {base/bull/bear: assumptions}
"""

import re
import json as _json
from datetime import date, datetime, timedelta
from pathlib import Path
import requests
import numpy as np
import pandas as pd
from yahooquery import Ticker
from config import settings


HEADERS = {
    "User-Agent": "InvestmentAgents/1.0 (contacto@valoracion.com)",
}


# --- Caché de datos financieros ---

def _cache_path(ticker: str, for_date: date = None) -> Path:
    """Ruta del archivo de caché para un ticker y fecha."""
    d = for_date or date.today()
    settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return settings.CACHE_DIR / f"{ticker}_{d.isoformat()}.json"


def _serialize_for_cache(data: dict) -> dict:
    """Convierte DataFrames a formato JSON-serializable para caché."""
    out = {}
    for key, val in data.items():
        if isinstance(val, pd.DataFrame):
            if val.empty:
                out[key] = {"__type__": "dataframe", "data": None}
            else:
                out[key] = {
                    "__type__": "dataframe",
                    "data": val.to_json(date_format="iso"),
                }
        else:
            out[key] = val
    return out


def _deserialize_from_cache(data: dict) -> dict:
    """Restaura DataFrames desde formato de caché."""
    out = {}
    for key, val in data.items():
        if isinstance(val, dict) and val.get("__type__") == "dataframe":
            if val["data"] is None:
                out[key] = pd.DataFrame()
            else:
                out[key] = pd.read_json(val["data"])
        else:
            out[key] = val
    return out


def _load_cache(ticker: str) -> dict | None:
    """Carga datos de caché del día actual. Devuelve None si no existe."""
    path = _cache_path(ticker)
    if not path.exists():
        return None
    try:
        raw = _json.loads(path.read_text(encoding="utf-8"))
        print(f"  [cache] Usando datos cacheados de {ticker} ({path.name})")
        return _deserialize_from_cache(raw)
    except Exception as e:
        print(f"  [cache] Error leyendo caché: {e}. Descargando datos frescos...")
        return None


def _save_cache(ticker: str, data: dict):
    """Guarda datos en caché."""
    path = _cache_path(ticker)
    try:
        serialized = _serialize_for_cache(data)
        path.write_text(_json.dumps(serialized, default=str, ensure_ascii=False),
                        encoding="utf-8")
        print(f"  [cache] Datos guardados en {path.name}")
    except Exception as e:
        print(f"  [cache] Error guardando caché: {e}")


def cleanup_cache():
    """Elimina archivos de caché más antiguos que CACHE_TTL_DAYS."""
    if not settings.CACHE_DIR.exists():
        return
    cutoff = date.today() - timedelta(days=settings.CACHE_TTL_DAYS)
    removed = 0
    for f in settings.CACHE_DIR.glob("*.json"):
        # Extraer fecha del nombre: TICKER_YYYY-MM-DD.json
        parts = f.stem.rsplit("_", 1)
        if len(parts) == 2:
            try:
                file_date = date.fromisoformat(parts[1])
                if file_date < cutoff:
                    f.unlink()
                    removed += 1
            except ValueError:
                continue
    if removed:
        print(f"  [cache] Limpieza: {removed} archivo(s) antiguo(s) eliminado(s)")


def search_ticker(query: str, max_results: int = 5) -> list[dict]:
    """
    Busca tickers en Yahoo Finance dado un nombre de empresa o ticker parcial.
    Devuelve lista de {symbol, name, exchange, type} ordenada por relevancia.

    Ejemplo:
        search_ticker("Watches of Switzerland") -> [{"symbol": "WOSG.L", "name": "Watches of Switzerland Group", ...}]
        search_ticker("Inditex") -> [{"symbol": "ITX.MC", ...}]
    """
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {
        "q": query,
        "quotesCount": max_results,
        "newsCount": 0,
        "enableFuzzyQuery": True,
        "quotesQueryId": "tss_match_phrase_query",
    }
    headers = {**HEADERS, "Accept": "application/json"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        results = []
        for q in data.get("quotes", []):
            if q.get("quoteType") not in ("EQUITY", "ETF"):
                continue
            results.append({
                "symbol": q.get("symbol", ""),
                "name": q.get("longname") or q.get("shortname", ""),
                "exchange": q.get("exchange", ""),
                "type": q.get("quoteType", ""),
            })
        return results
    except Exception as e:
        print(f"  [ticker_search] Error: {e}")
        return []


def resolve_ticker(query: str) -> str | None:
    """
    Dado un nombre de empresa o ticker sin sufijo, devuelve el ticker correcto de Yahoo Finance.
    Devuelve None si no encuentra nada.

    Ejemplo:
        resolve_ticker("Watches of Switzerland") -> "WOSG.L"
        resolve_ticker("Inditex") -> "ITX.MC"
        resolve_ticker("AAPL") -> "AAPL"
    """
    results = search_ticker(query, max_results=5)
    if not results:
        return None
    return results[0]["symbol"]


def get_company_data(ticker: str) -> dict:
    """
    Obtiene todos los datos financieros necesarios para la valoracion.
    Usa caché del día si existe (salvo FORCE_FRESH).
    """
    # Intentar caché (salvo --fresh)
    if not settings.FORCE_FRESH:
        cached = _load_cache(ticker)
        if cached is not None:
            return cached

    print(f"  [data] Descargando datos financieros para {ticker}...")

    stock = Ticker(ticker)

    def _safe_fetch(prop):
        result = prop
        if not isinstance(result, dict):
            return {}
        val = result.get(ticker, {})
        return val if isinstance(val, dict) else {}

    price_data = _safe_fetch(stock.price)
    fin_data = _safe_fetch(stock.financial_data)
    profile = _safe_fetch(stock.summary_profile)
    key_stats = _safe_fetch(stock.key_stats)
    summary = _safe_fetch(stock.summary_detail)

    info = _build_info_dict(price_data, fin_data, profile, key_stats, summary, ticker)
    print(f"    Empresa: {info.get('longName', ticker)}")
    print(f"    Sector: {info.get('sector', 'N/A')}")

    income_stmt = _pivot_financial_df(stock.income_statement(frequency='a'), ticker)
    balance_sheet = _pivot_financial_df(stock.balance_sheet(frequency='a'), ticker)
    cash_flow = _pivot_financial_df(stock.cash_flow(frequency='a'), ticker)

    print(f"    Income Statement: {len(income_stmt.columns)} periodos")
    print(f"    Balance Sheet: {len(balance_sheet.columns)} periodos")
    print(f"    Cash Flow: {len(cash_flow.columns)} periodos")

    current_price = fin_data.get("currentPrice", 0) or price_data.get("regularMarketPrice", 0)
    shares_outstanding = key_stats.get("sharesOutstanding", 0) or key_stats.get("impliedSharesOutstanding", 0) or 0

    estimates = _get_analyst_estimates(info, fin_data)
    segments = _get_business_segments(ticker, info, income_stmt)

    try:
        hist = stock.history(period="5y", interval="1mo")
        if isinstance(hist, dict):
            hist = pd.DataFrame()
        elif isinstance(hist, pd.DataFrame) and not hist.empty:
            if isinstance(hist.index, pd.MultiIndex):
                hist = hist.reset_index(level=0, drop=True)
        else:
            hist = pd.DataFrame()
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

    # Guardar en caché y limpiar archivos antiguos
    _save_cache(ticker, result)
    cleanup_cache()

    return result


def _build_info_dict(price_data, fin_data, profile, key_stats, summary, ticker):
    info = {}
    if isinstance(price_data, dict):
        info["longName"] = price_data.get("longName") or price_data.get("shortName", ticker)
        info["regularMarketPrice"] = price_data.get("regularMarketPrice", 0)
        info["marketCap"] = price_data.get("marketCap", 0)
        info["currency"] = price_data.get("currency", "USD")
    if isinstance(profile, dict):
        info["sector"] = profile.get("sector", "")
        info["industry"] = profile.get("industry", "")
        info["longBusinessSummary"] = profile.get("longBusinessSummary", "")
        info["country"] = profile.get("country", "")
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
    if isinstance(key_stats, dict):
        info["beta"] = key_stats.get("beta", 1.0)
        info["sharesOutstanding"] = key_stats.get("sharesOutstanding", 0)
        info["forwardPE"] = key_stats.get("forwardPE", 0)
        info["enterpriseToEbitda"] = key_stats.get("enterpriseToEbitda", 0)
    if isinstance(summary, dict):
        info["trailingPE"] = summary.get("trailingPE", 0)
        info["dividendYield"] = summary.get("dividendYield", 0)
        info["fiftyTwoWeekHigh"] = summary.get("fiftyTwoWeekHigh", 0)
        info["fiftyTwoWeekLow"] = summary.get("fiftyTwoWeekLow", 0)
    return info


def _pivot_financial_df(df, ticker):
    if df is None or (isinstance(df, str) and "error" in df.lower()):
        return pd.DataFrame()
    if isinstance(df, pd.DataFrame) and not df.empty:
        if 'symbol' in df.columns:
            df = df[df['symbol'] == ticker].copy()
        elif isinstance(df.index, pd.MultiIndex):
            try:
                df = df.loc[ticker].copy()
            except KeyError:
                return pd.DataFrame()
        if 'asOfDate' not in df.columns:
            return pd.DataFrame()
        if 'periodType' in df.columns:
            df = df[df['periodType'] == '12M'].copy()
            if df.empty:
                return pd.DataFrame()
        df = df.set_index('asOfDate')
        drop_cols = ['periodType', 'currencyCode', 'symbol']
        df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
        df = df.T
        df.columns = pd.to_datetime(df.columns)
        df = df[sorted(df.columns)]
        return df
    return pd.DataFrame()


def _get_analyst_estimates(info, fin_data):
    growth = info.get("revenueGrowth", 0) or 0
    return {
        "revenue_growth": {"current": growth},
        "target_prices": {
            "high": info.get("targetHighPrice", 0) or 0,
            "low": info.get("targetLowPrice", 0) or 0,
            "mean": info.get("targetMeanPrice", 0) or 0,
            "current": info.get("currentPrice", 0) or 0,
        },
    }


def _get_business_segments(ticker, info, income_stmt):
    segments = []
    if "." not in ticker:
        segments = _try_sec_segments(ticker)
    if segments:
        print(f"    Segmentos (SEC): {len(segments)}")
        return segments
    segments = _generate_fallback_segments(info, income_stmt)
    print(f"    Segmentos (fallback): {len(segments)}")
    return segments


def _try_sec_segments(ticker):
    try:
        resp = requests.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=15)
        data = resp.json()
        cik = None
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                cik = str(entry["cik_str"]).zfill(10)
                break
        if not cik:
            return []
        resp = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return []
        us_gaap = resp.json().get("facts", {}).get("us-gaap", {})
        segment_data = {}
        for key in ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "Revenue",
                     "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"]:
            if key in us_gaap:
                for entry in us_gaap[key].get("units", {}).get("USD", []):
                    segment = entry.get("segment")
                    if segment and entry.get("form") == "10-K":
                        seg_label = segment.get("value", "")
                        if seg_label and ":" in seg_label:
                            seg_label = seg_label.split(":")[-1]
                        if seg_label:
                            segment_data.setdefault(seg_label, {})[entry.get("fy")] = entry.get("val", 0)
                if segment_data:
                    break
        if not segment_data:
            return []
        segments = []
        for name, years_data in segment_data.items():
            clean_name = name.replace("Member", "").replace("Segment", "")
            clean_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', clean_name).strip()
            if clean_name and years_data:
                segments.append({"name": clean_name, "revenues": years_data})
        return segments
    except Exception as e:
        print(f"    Aviso: Error obteniendo segmentos SEC: {e}")
        return []


def _generate_fallback_segments(info, income_stmt):
    total_revenues = {}
    if income_stmt is not None and not income_stmt.empty:
        for col in income_stmt.columns:
            rev = _safe_get(income_stmt, "TotalRevenue", col) or _safe_get(income_stmt, "Total Revenue", col)
            if rev and not np.isnan(rev):
                total_revenues[col.year] = float(rev)
    return [{"name": info.get("industry") or info.get("sector") or "Principal", "revenues": total_revenues, "pct": 1.0}]


def extract_historical_data(data):
    income = data["income_stmt"]
    balance = data["balance_sheet"]
    cashflow = data["cash_flow"]
    years_data = {}

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
            if not yr["gross_profit"] and yr["total_revenue"] and yr["cost_of_revenue"]:
                yr["gross_profit"] = yr["total_revenue"] - abs(yr["cost_of_revenue"])
            if not yr["ebitda"] and yr["operating_income"] and yr["depreciation"]:
                yr["ebitda"] = yr["operating_income"] + abs(yr["depreciation"])
            years_data[year] = yr

    if balance is not None and not balance.empty:
        for col in balance.columns:
            year = col.year
            yr = years_data.setdefault(year, {})
            yr["total_assets"] = _safe_get_multi(balance, ["TotalAssets", "Total Assets"], col)
            yr["total_liabilities"] = _safe_get_multi(balance, ["TotalLiabilitiesNetMinorityInterest", "Total Liabilities Net Minority Interest"], col)
            yr["total_equity"] = _safe_get_multi(balance, ["TotalEquityGrossMinorityInterest", "StockholdersEquity", "CommonStockEquity"], col)
            yr["cash"] = _safe_get_multi(balance, ["CashAndCashEquivalents", "Cash And Cash Equivalents", "CashCashEquivalentsAndShortTermInvestments", "CashFinancial"], col)
            yr["total_debt"] = _safe_get_multi(balance, ["TotalDebt", "Total Debt", "LongTermDebt"], col)
            yr["current_assets"] = _safe_get_multi(balance, ["CurrentAssets", "Current Assets"], col)
            yr["current_liabilities"] = _safe_get_multi(balance, ["CurrentLiabilities", "Current Liabilities"], col)
            yr["net_ppe"] = _safe_get_multi(balance, ["NetPPE", "Net PPE", "GrossPPE"], col)
            yr["goodwill"] = _safe_get_multi(balance, ["Goodwill"], col)
            yr["intangible_assets"] = _safe_get_multi(balance, ["IntangibleAssets", "OtherIntangibleAssets", "GoodwillAndOtherIntangibleAssets"], col)

    if cashflow is not None and not cashflow.empty:
        for col in cashflow.columns:
            year = col.year
            yr = years_data.setdefault(year, {})
            yr["operating_cashflow"] = _safe_get_multi(cashflow, ["OperatingCashFlow", "Operating Cash Flow"], col)
            yr["capex"] = _safe_get_multi(cashflow, ["CapitalExpenditure", "Capital Expenditure"], col)
            yr["free_cashflow"] = _safe_get_multi(cashflow, ["FreeCashFlow", "Free Cash Flow"], col)
            yr["depreciation_cf"] = _safe_get_multi(cashflow, ["DepreciationAndAmortization", "Depreciation And Amortization"], col)
            yr["stock_based_comp"] = _safe_get_multi(cashflow, ["StockBasedCompensation", "Stock Based Compensation"], col)
            yr["change_working_capital"] = _safe_get_multi(cashflow, ["ChangeInWorkingCapital", "Change In Working Capital"], col)
            if not yr.get("free_cashflow") and yr.get("operating_cashflow") and yr.get("capex"):
                yr["free_cashflow"] = yr["operating_cashflow"] + yr["capex"]

    return {y: d for y, d in years_data.items() if d.get("total_revenue", 0) != 0}


def generate_scenarios(data, historical):
    info = data["info"]
    estimates = data["estimates"]
    segments = data["segments"]

    sorted_years = sorted(historical.keys())
    revenue_growths = []
    for i in range(1, len(sorted_years)):
        prev = historical[sorted_years[i-1]].get("total_revenue", 0)
        curr = historical[sorted_years[i]].get("total_revenue", 0)
        if prev and curr and prev > 0:
            revenue_growths.append(curr / prev - 1)

    avg_growth = np.mean(revenue_growths) if revenue_growths else 0.05
    margins = _calculate_avg_margins(historical, sorted_years)

    analyst_growth = estimates.get("revenue_growth", {}).get("current", None)
    base_growth = analyst_growth if analyst_growth and analyst_growth != 0 else avg_growth
    base_growth = max(min(base_growth, 0.40), -0.15)

    # Offsets calibrados para dispersión profesional (~1.6-1.8x bull/bear)
    # Growth: ±15% del base (vs ±30% anterior)
    bull_premium = max(abs(base_growth) * 0.15, 0.015)
    bear_discount = max(abs(base_growth) * 0.15, 0.015)
    wacc_base = _estimate_wacc(info)
    tv_base = _estimate_terminal_multiple(info)

    def _tapering(g, i, positive):
        if positive:
            # Crecimiento positivo: desacelera gradualmente (10% menos cada año)
            return g * (1 - 0.1 * i)
        # Crecimiento negativo: recupera hacia 0 y luego crece ligeramente
        # Ej: -5% Y1 → -2% Y2 → +1% Y3 → +3% Y4 → +4% Y5
        recovery = g + 0.02 * (i + 1)
        return min(recovery, 0.05)  # Cap en 5% de crecimiento post-recuperación

    # Offsets calibrados para dispersión profesional (~1.5-1.8x bull/bear):
    #   Growth: ±15% del base
    #   Gross margin: ±1pp
    #   SGA: ±0.5pp
    #   R&D: sin cambio bear/bull
    #   CapEx: bear 1.15x (menos eficiencia), bull 0.90x (más eficiencia)
    #   WACC: ±1pp simétrico
    #   TV Multiple: ±2 simétrico
    scenarios = {}
    for key, name, g_offset, gm_off, sga_off, rd_off, capex_mult, wacc_off, tv_off in [
        ("base", "Base Case", 0, 0, 0, 0, 1.0, 0, 0),
        ("bull", "Bull Case", bull_premium, 0.01, -0.005, 0, 0.90, -0.01, 2),
        ("bear", "Bear Case", -bear_discount, -0.01, 0.005, 0, 1.15, 0.01, -2),
    ]:
        g = base_growth + g_offset
        sc = {"name": name}
        for y in range(1, 6):
            sc[f"revenue_growth_y{y}"] = _tapering(g, y - 1, g > 0)
        sc["gross_margin"] = max(min(margins["gross_margin"] + gm_off, 0.95), 0.1)
        sc["sga_pct"] = max(margins["sga_pct"] + sga_off, 0.01)
        sc["rd_pct"] = margins["rd_pct"] + rd_off
        sc["da_pct"] = margins["da_pct"]
        sc["capex_pct"] = margins["capex_pct"] * capex_mult
        sc["tax_rate"] = margins["tax_rate"]
        sc["wacc"] = wacc_base + wacc_off
        sc["terminal_multiple"] = max(tv_base + tv_off, 5)
        sc["segments"] = [{"name": s["name"], "growth_rates": [sc[f"revenue_growth_y{y}"] for y in range(1, 6)]} for s in segments]
        scenarios[key] = sc

    # Sanity check: EBITDA implícito vs real
    # Si el margen EBITDA implícito (GM - SGA - R&D) difiere >10pp del real, ajustar SGA
    latest_year = sorted_years[-1] if sorted_years else None
    if latest_year:
        real_rev = historical[latest_year].get("total_revenue", 0)
        real_ebitda = historical[latest_year].get("ebitda", 0)
        if real_rev and real_ebitda:
            real_ebitda_margin = real_ebitda / real_rev
            base_sc = scenarios["base"]
            implicit_ebitda_margin = base_sc["gross_margin"] - base_sc["sga_pct"] - base_sc["rd_pct"]
            gap = real_ebitda_margin - implicit_ebitda_margin
            if abs(gap) > 0.05:  # >5pp de diferencia
                # Ajustar SGA para que el EBITDA implícito coincida con el real
                for key in scenarios:
                    scenarios[key]["sga_pct"] = max(scenarios[key]["sga_pct"] - gap, 0.01)

    return scenarios


def _calculate_avg_margins(historical, sorted_years):
    gm, sga, rd, da, capex, tax = [], [], [], [], [], []
    for year in sorted_years:
        yr = historical[year]
        rev = yr.get("total_revenue", 0)
        if not rev:
            continue
        if yr.get("gross_profit"):
            gm.append(yr["gross_profit"] / rev)
        if yr.get("selling_general_admin"):
            sga.append(abs(yr["selling_general_admin"]) / rev)
        if yr.get("research_development"):
            rd.append(abs(yr["research_development"]) / rev)
        d = yr.get("depreciation", 0) or yr.get("depreciation_cf", 0)
        if d:
            da.append(abs(d) / rev)
        if yr.get("capex"):
            capex.append(abs(yr["capex"]) / rev)
        t = yr.get("tax_provision", 0)
        ebt = yr.get("operating_income", 0)
        if t and ebt and ebt > 0:
            tax.append(abs(t) / ebt)
    return {
        "gross_margin": np.mean(gm) if gm else 0.40,
        "sga_pct": np.mean(sga) if sga else 0.15,
        "rd_pct": np.mean(rd) if rd else 0.0,  # 0 si no hay datos (no inventar R&D)
        "da_pct": np.mean(da) if da else 0.03,
        "capex_pct": np.mean(capex) if capex else 0.04,
        "tax_rate": min(np.mean(tax), 0.35) if tax else 0.21,
    }


def _estimate_wacc(info):
    beta = info.get("beta", 1.0) or 1.0
    ke = 0.045 + abs(beta) * 0.055
    mc = info.get("marketCap", 0) or 0
    td = info.get("totalDebt", 0) or 0
    ew = mc / (mc + td) if mc > 0 else 0.8
    return round(max(ke * ew + 0.05 * (1 - 0.21) * (1 - ew), 0.05), 4)


SECTOR_TV = {"Technology": 18, "Communication Services": 14, "Consumer Cyclical": 12,
             "Consumer Defensive": 11, "Healthcare": 15, "Financial Services": 10,
             "Industrials": 11, "Energy": 8, "Utilities": 9, "Real Estate": 12, "Basic Materials": 9}

# Industrias premium que merecen múltiplos más altos dentro de su sector
INDUSTRY_TV_BONUS = {
    "Luxury Goods": 4, "Apparel - Luxury": 4,
    "Software - Infrastructure": 4, "Software - Application": 4,
    "Semiconductors": 3, "Internet Content & Information": 3,
    "Drug Manufacturers": 3, "Biotechnology": 2,
    "Aerospace & Defense": 2,
}


def _estimate_terminal_multiple(info):
    m = SECTOR_TV.get(info.get("sector", ""), 12)
    # Bonus por industria premium
    industry = info.get("industry", "")
    m += INDUSTRY_TV_BONUS.get(industry, 0)
    # Ajuste por crecimiento (solo para growth sostenido, no penalizar baches cíclicos)
    g = info.get("revenueGrowth", 0) or 0
    if g > 0.20: m += 3
    elif g > 0.10: m += 1
    # No penalizar growth negativo — puede ser un bache cíclico, no estructural
    return max(m, 5)


def _safe_get(df, key, col):
    try:
        if key in df.index:
            val = df.loc[key, col]
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                return float(val)
    except Exception:
        pass
    return 0


def _safe_get_multi(df, keys, col):
    for key in keys:
        val = _safe_get(df, key, col)
        if val != 0:
            return val
    return 0


def get_current_prices(tickers: list[str]) -> dict[str, float]:
    """Obtiene precios actuales para una lista de tickers via yahooquery."""
    if not tickers:
        return {}
    stock = Ticker(tickers)
    prices = stock.price
    result = {}
    for t in tickers:
        try:
            p = prices[t]
            if isinstance(p, dict):
                result[t] = p.get("regularMarketPrice", 0)
        except Exception:
            continue
    return result
