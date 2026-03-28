"""
Analyst Agent — valoracion completa de una empresa.

Flujo:
1. Crea carpeta data/valuations/{TICKER}/
2. Descarga 10-K filings de SEC (solo EEUU)
3. Obtiene datos financieros via yahooquery
4. Extrae historicos y genera 3 escenarios
5. Busca noticias recientes
6. Genera Excel completo (4 hojas con formulas reales)
7. Guarda JSON resumen para thesis_writer

Output:
    data/valuations/{TICKER}/
    ├── SEC_filings/          (solo EEUU)
    ├── {TICKER}_modelo_valoracion.xlsx
    └── {TICKER}_valuation.json
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

from config.settings import VALUATIONS_DIR
from tools.financial_data import get_company_data, extract_historical_data, generate_scenarios, DataQualityError
from tools.excel_generator import generate_valuation_excel
from tools.sec_downloader import download_10k_filings
from tools.news_fetcher import fetch_news
from agents.base import call_agent
from config.prompts import QUICK_VALUATION


def quick_summary(ticker: str) -> str:
    """Genera resumen rápido con 3 escenarios + conclusión desde la valoración existente."""
    valuation = load_valuation(ticker)
    if valuation is None:
        raise ValueError(f"No existe valoración para {ticker}. Ejecuta primero: python main.py --analyst {ticker}")
    return call_agent(
        system_prompt=QUICK_VALUATION,
        user_message=json.dumps(valuation, ensure_ascii=False),
        model_tier="quick",
        max_tokens=800,
    )


def _is_us_ticker(ticker: str) -> bool:
    return "." not in ticker


def _clean_ticker(ticker: str) -> str:
    return ticker.replace(".", "_")


_CURRENCY_MAP = {
    ".AX": "A$", ".L": "GBP ", ".TO": "C$", ".V": "C$",
    ".MC": "EUR ", ".PA": "EUR ", ".DE": "EUR ", ".AS": "EUR ",
    ".BR": "EUR ", ".MI": "EUR ", ".SW": "CHF ",
    ".HK": "HK$", ".T": "JPY ", ".TW": "NT$",
    ".NS": "INR ", ".BO": "INR ",
    ".SA": "R$", ".MX": "MX$",
    ".KS": "KRW ", ".SI": "S$",
}


def _get_currency_symbol(ticker: str) -> str:
    for suffix, symbol in _CURRENCY_MAP.items():
        if ticker.endswith(suffix):
            return symbol
    return "$"


def run_analyst(ticker: str) -> dict:
    """
    Valoracion completa de una empresa. Genera carpeta con Excel y JSON.

    Args:
        ticker: Simbolo bursatil (ej: "AAPL", "TEF.MC", "BATS.L")

    Returns:
        dict con toda la info de valoracion + paths de archivos generados
    """
    folder_name = _clean_ticker(ticker)
    currency = _get_currency_symbol(ticker)
    is_us = _is_us_ticker(ticker)

    output_dir = VALUATIONS_DIR / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    print(f"\n{'='*60}")
    print(f"  Valoracion de {ticker}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # PASO 1: SEC Filings (solo EEUU)
    downloaded_files = []
    if is_us:
        print(f"\n--- PASO 1/5: SEC EDGAR (10-K) ---")
        try:
            sec_dir = str(output_dir / "SEC_filings")
            downloaded_files = download_10k_filings(ticker, sec_dir)
            print(f"    {len(downloaded_files)} filings descargados")
        except Exception as e:
            print(f"    Aviso: Error SEC filings: {e}")
    else:
        print(f"\n--- PASO 1/5: Filings ---")
        print(f"    Ticker internacional ({ticker}): SEC no aplica")

    # PASO 2: Datos financieros
    print(f"\n--- PASO 2/5: Datos financieros (yahooquery) ---")
    try:
        data = get_company_data(ticker)
    except DataQualityError as e:
        print(f"\n  [ERROR] {e}")
        print(f"  No se puede generar valoración con datos inválidos.")
        return {"error": str(e), "ticker": ticker}
    historical = extract_historical_data(data)
    scenarios = generate_scenarios(data, historical)

    company_name = data["info"].get("longName", ticker)
    current_price = data["current_price"]

    print(f"\n    Resumen:")
    print(f"    Empresa: {company_name}")
    print(f"    Precio actual: {currency}{current_price:,.2f}")
    print(f"    Anios historicos: {sorted(historical.keys())}")
    print(f"    Segmentos: {[s['name'] for s in data['segments']]}")
    for k, v in scenarios.items():
        if k.startswith("_"):
            continue
        print(f"    {k.capitalize()}: Growth Y1={v['revenue_growth_y1']:.1%}, "
              f"WACC={v['wacc']:.1%}, TV={v['terminal_multiple']:.0f}x")

    # PASO 2.5: Auditoría SEC 10-K (solo EEUU)
    sec_audit = None
    if is_us and downloaded_files:
        try:
            from tools.sec_parser import audit_company
            sec_audit = audit_company(ticker, str(output_dir))
            if sec_audit.get("has_10k"):
                confidence = sec_audit.get("confidence", "N/A")
                alerts = sec_audit.get("alerts", [])
                if alerts:
                    print(f"  [!] SEC AUDIT ({confidence}): {len(alerts)} discrepancia(s) Yahoo vs 10-K")
                    for a in alerts:
                        print(f"      [{a['level'].upper()}] {a['message']}")
                else:
                    print(f"  [OK] SEC AUDIT: datos Yahoo coinciden con 10-K")
        except Exception as e:
            print(f"  [!] SEC audit error: {e}")

    # PASO 3: Noticias
    print(f"\n--- PASO 3/5: Noticias recientes ---")
    try:
        news = fetch_news(ticker, company_name)
        print(f"    {len(news)} noticias encontradas")
    except Exception as e:
        print(f"    Aviso: Error noticias: {e}")
        news = []

    # Si se detectó adquisición, buscar noticias de M&A específicas
    if scenarios.get("_acquisition_detected"):
        try:
            from tools.news_fetcher import get_ticker_news
            import urllib.parse
            from tools.news_fetcher import _fetch_rss
            acq_query = urllib.parse.quote(f"{company_name} acquisition merger")
            acq_url = f"https://news.google.com/rss/search?q={acq_query}&hl=en-US&gl=US&ceid=US:en"
            acq_news = _fetch_rss(acq_url, 10, "Google News M&A")
            if acq_news:
                news.extend(acq_news)
                print(f"    +{len(acq_news)} noticias de M&A encontradas")
        except Exception:
            pass

    # PASO 4: Excel
    print(f"\n--- PASO 4/5: Modelo Excel ---")
    excel_path = str(output_dir / f"{folder_name}_modelo_valoracion.xlsx")
    generate_valuation_excel(ticker, data, historical, scenarios, excel_path)

    # PASO 5: JSON resumen (para thesis_writer)
    print(f"\n--- PASO 5/5: Guardando resumen ---")
    valuation_summary = _build_valuation_summary(
        ticker, company_name, data, historical, scenarios, news,
        excel_path, downloaded_files, currency, sec_audit
    )
    # Guardar versión actual (backward compat)
    json_path = str(output_dir / f"{folder_name}_valuation.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(valuation_summary, f, ensure_ascii=False, indent=2, default=str)
    print(f"    JSON guardado: {json_path}")

    # Guardar versión con timestamp + actualizar historial
    _save_versioned(output_dir, folder_name, valuation_summary)

    # Resumen final
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  VALORACION COMPLETADA: {company_name} ({ticker})")
    print(f"{'='*60}")
    print(f"  Tiempo: {elapsed:.1f}s")
    print(f"  Archivos:")
    print(f"    {output_dir}/")
    if downloaded_files:
        print(f"    ├── SEC_filings/ ({len(downloaded_files)} filings)")
    print(f"    ├── {folder_name}_modelo_valoracion.xlsx")
    print(f"    └── {folder_name}_valuation.json")
    print(f"  Precio actual: {currency}{current_price:,.2f}")
    print(f"  WACC (Base): {scenarios['base']['wacc']:.1%}")
    print(f"  TV Multiple (Base): {scenarios['base']['terminal_multiple']:.0f}x")

    return valuation_summary


def get_valuation_path(ticker: str) -> Path | None:
    """Retorna el path del JSON de valoracion si existe."""
    folder_name = _clean_ticker(ticker)
    json_path = VALUATIONS_DIR / folder_name / f"{folder_name}_valuation.json"
    return json_path if json_path.exists() else None


def load_valuation(ticker: str) -> dict | None:
    """Carga la valoracion existente de un ticker."""
    path = get_valuation_path(ticker)
    if path is None:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_valuation_summary(ticker, company_name, data, historical, scenarios, news,
                              excel_path, sec_files, currency, sec_audit=None):
    """Construye el dict resumen completo de la valoracion."""
    info = data["info"]
    sorted_years = sorted(historical.keys())

    latest = historical.get(sorted_years[-1], {}) if sorted_years else {}
    rev = latest.get("total_revenue", 0)
    ni = latest.get("net_income", 0)
    fcf = latest.get("free_cashflow", 0)
    ebitda = latest.get("ebitda", 0)

    return {
        "ticker": ticker,
        "company": company_name,
        "currency": currency,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "current_price": data["current_price"],
        "shares_outstanding": data["shares_outstanding"],
        "market_cap": info.get("marketCap", 0),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "country": info.get("country", ""),
        "business_summary": info.get("longBusinessSummary", ""),
        "beta": info.get("beta", 1.0),
        "analyst_targets": data["estimates"].get("target_prices", {}),
        "historical_years": sorted_years,
        "latest_financials": {
            "revenue": rev,
            "net_income": ni,
            "ebitda": ebitda,
            "free_cashflow": fcf,
            "gross_margin": latest.get("gross_profit", 0) / rev if rev else 0,
            "operating_margin": latest.get("operating_income", 0) / rev if rev else 0,
            "net_margin": ni / rev if rev else 0,
            "total_debt": latest.get("total_debt", 0),
            "cash": latest.get("cash", 0),
            "total_equity": latest.get("total_equity", 0),
        },
        "historical_data": {str(y): _summarize_year(d) for y, d in historical.items()},
        "segments": [{"name": s["name"], "revenues": s.get("revenues", {})} for s in data["segments"]],
        "acquisition_detected": scenarios.get("_acquisition_detected"),
        "captive_finance": scenarios.get("_captive_finance"),
        "sec_audit": {
            "confidence": sec_audit.get("confidence"),
            "alerts": sec_audit.get("alerts", []),
            "comparisons": sec_audit.get("comparisons", []),
        } if sec_audit and sec_audit.get("has_10k") else None,
        "scenarios": {
            k: {
                "revenue_growth_y1": v["revenue_growth_y1"],
                "revenue_growth_y5": v["revenue_growth_y5"],
                "gross_margin": v["gross_margin"],
                "sga_pct": v.get("sga_pct"),
                "rd_pct": v.get("rd_pct"),
                "da_pct": v.get("da_pct"),
                "capex_pct": v.get("capex_pct"),
                "tax_rate": v.get("tax_rate"),
                "wacc": v["wacc"],
                "terminal_multiple": v["terminal_multiple"],
            }
            for k, v in scenarios.items() if not k.startswith("_")
        },
        "news": [{"title": n["title"], "date": n["date"], "source": n.get("source", "")} for n in news[:10]],
        "files": {
            "excel": excel_path,
            "sec_filings": sec_files,
        },
    }


def _summarize_year(d):
    return {
        "revenue": d.get("total_revenue", 0),
        "net_income": d.get("net_income", 0),
        "ebitda": d.get("ebitda", 0),
        "fcf": d.get("free_cashflow", 0),
        "operating_income": d.get("operating_income", 0),
    }


# --- Versionado de análisis ---

def _save_versioned(output_dir: Path, folder_name: str, valuation: dict):
    """Guarda copia con timestamp y actualiza history.json."""
    today = datetime.now().strftime("%Y%m%d")
    versioned_path = output_dir / f"{folder_name}_{today}_valuation.json"
    with open(versioned_path, "w", encoding="utf-8") as f:
        json.dump(valuation, f, ensure_ascii=False, indent=2, default=str)

    # Extraer métricas clave para el historial
    scenarios = valuation.get("scenarios", {})
    entry = {
        "date": valuation.get("date", today),
        "file": versioned_path.name,
        "current_price": valuation.get("current_price", 0),
        "currency": valuation.get("currency", "$"),
        "fair_value_bear": scenarios.get("bear", {}).get("wacc", 0),
        "fair_value_base": scenarios.get("base", {}).get("wacc", 0),
        "fair_value_bull": scenarios.get("bull", {}).get("wacc", 0),
        "revenue": valuation.get("latest_financials", {}).get("revenue", 0),
        "gross_margin": valuation.get("latest_financials", {}).get("gross_margin", 0),
        "growth_y1_base": scenarios.get("base", {}).get("revenue_growth_y1", 0),
        "wacc_base": scenarios.get("base", {}).get("wacc", 0),
        "tv_base": scenarios.get("base", {}).get("terminal_multiple", 0),
    }

    # Leer/crear historial
    history_path = output_dir / "history.json"
    history = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            history = []

    # Reemplazar entrada del mismo día si existe, si no añadir
    history = [h for h in history if h.get("date") != entry["date"]]
    history.append(entry)
    history.sort(key=lambda h: h["date"])

    history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False, default=str),
                            encoding="utf-8")
    print(f"    Versión guardada: {versioned_path.name} ({len(history)} en historial)")


def load_history(ticker: str) -> list[dict]:
    """Carga el historial de valoraciones de un ticker."""
    folder_name = _clean_ticker(ticker)
    history_path = VALUATIONS_DIR / folder_name / "history.json"
    if not history_path.exists():
        return []
    try:
        return json.loads(history_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception):
        return []
