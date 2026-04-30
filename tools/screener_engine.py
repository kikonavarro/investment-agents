"""
Screener Engine — filtros cuantitativos sobre universo de acciones.
Todo en Python. Claude no ve los datos crudos, solo el top-15 comprimido.
"""
import json as _json
from datetime import date, timedelta
import yfinance as yf
import pandas as pd
import yaml
from pathlib import Path

from config import settings

FILTERS_FILE = Path(__file__).parent.parent / "config" / "screener_filters.yaml"
UNIVERSE_CACHE_DIR = settings.CACHE_DIR

# Fallback: listas hardcodeadas por si falla la descarga de Wikipedia
_FALLBACK_UNIVERSES = {
    "SP500": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "BRK-B", "JNJ",
        "JPM", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL", "BAC", "ADBE",
        "NFLX", "CRM", "XOM", "CVX", "KO", "PEP", "MCD", "WMT", "ABBV",
        "TMO", "ABT", "COST", "ACN", "NKE", "AVGO", "TXN", "QCOM", "LLY",
        "DHR", "NEE", "LOW", "UNP", "RTX", "HON", "PM", "MO", "BTI",
    ],
    "IBEX35": [
        "SAN.MC", "BBVA.MC", "TEF.MC", "ITX.MC", "IBE.MC", "REP.MC",
        "AMS.MC", "MAP.MC", "GRF.MC", "FER.MC", "ACS.MC", "AENA.MC",
        "ELE.MC", "NTGY.MC", "MTS.MC", "CABK.MC",
    ],
    "EUROSTOXX600": [
        "NESN.SW", "NOVN.SW", "ROG.SW", "ASML.AS", "MC.PA", "SAP.DE",
        "SIE.DE", "ABI.BR", "AI.PA", "OR.PA", "BNP.PA", "SAN.PA",
        "BATS.L", "GSK.L", "AZN.L", "SHEL.L", "BP.L", "ULVR.L",
        "VOW3.DE", "BMW.DE", "MBG.DE", "BAYN.DE", "ALV.DE",
    ],
}

# URLs de Wikipedia con listas de componentes de índices
_WIKI_URLS = {
    "SP500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "IBEX35": "https://en.wikipedia.org/wiki/IBEX_35",
}


def _fetch_universe(market: str) -> list[str]:
    """Descarga componentes del índice desde Wikipedia. Cachea 30 días."""
    UNIVERSE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Comprobar caché
    cache_path = UNIVERSE_CACHE_DIR / f"universe_{market}.json"
    if cache_path.exists():
        try:
            cached = _json.loads(cache_path.read_text(encoding="utf-8"))
            cached_date = date.fromisoformat(cached.get("date", "2000-01-01"))
            if date.today() - cached_date < timedelta(days=30):
                return cached["tickers"]
        except (ValueError, KeyError, _json.JSONDecodeError):
            pass

    url = _WIKI_URLS.get(market)
    if not url:
        return _FALLBACK_UNIVERSES.get(market, [])

    try:
        print(f"  [screener] Descargando componentes de {market} desde Wikipedia...")
        tables = pd.read_html(url)
        tickers = []

        if market == "SP500" and len(tables) > 0:
            # La primera tabla tiene columna "Symbol"
            df = tables[0]
            col = "Symbol" if "Symbol" in df.columns else df.columns[0]
            tickers = df[col].dropna().str.strip().str.replace(".", "-", regex=False).tolist()

        elif market == "IBEX35" and len(tables) > 0:
            # Buscar tabla con columna Ticker
            for t in tables:
                for c in t.columns:
                    if "ticker" in str(c).lower() or "symbol" in str(c).lower():
                        raw = t[c].dropna().str.strip().tolist()
                        tickers = [f"{tk}.MC" if not tk.endswith(".MC") else tk for tk in raw]
                        break
                if tickers:
                    break

        if tickers:
            # Guardar en caché
            cache_data = {"date": date.today().isoformat(), "market": market, "tickers": tickers}
            cache_path.write_text(_json.dumps(cache_data, ensure_ascii=False), encoding="utf-8")
            print(f"  [screener] {len(tickers)} componentes de {market} cacheados")
            return tickers

    except Exception as e:
        print(f"  [screener] Error descargando {market}: {e}. Usando fallback.")

    return _FALLBACK_UNIVERSES.get(market, [])


def _get_universe(market: str) -> list[str]:
    """Obtiene universo: intenta Wikipedia primero, fallback a lista hardcodeada."""
    tickers = _fetch_universe(market)
    if not tickers:
        tickers = _FALLBACK_UNIVERSES.get(market, [])
    return tickers


def run_screen(filter_name: str = "graham_default", markets: list[str] = None) -> list[dict]:
    """
    Escanea el universo y devuelve candidatas que pasan los filtros.

    Args:
        filter_name: Nombre del filtro en screener_filters.yaml
        markets: Lista de mercados a escanear (None = SP500 por defecto)

    Returns:
        Lista de dicts con métricas de las candidatas, ordenadas por score.
    """
    filters = _load_filters(filter_name)
    if markets is None:
        markets = ["SP500"]

    # Construir universo (dinámico desde Wikipedia o fallback)
    tickers = []
    for market in markets:
        tickers.extend(_get_universe(market))
    tickers = list(set(tickers))  # Deduplicar

    print(f"  [screener] Analizando {len(tickers)} tickers con filtros '{filter_name}'...")

    candidates = []
    for i, ticker in enumerate(tickers):
        if i % 10 == 0:
            print(f"  [screener] Progreso: {i}/{len(tickers)}...")
        try:
            data = _get_screening_data(ticker)
            if data and _passes_filters(data, filters):
                data["score"] = _calc_score(data, filters)
                candidates.append(data)
        except Exception:
            continue

    # Ordenar por score descendente
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    print(f"  [screener] {len(candidates)} candidatas encontradas de {len(tickers)} analizadas.")
    return candidates


def _get_screening_data(ticker: str) -> dict | None:
    """Descarga métricas básicas para screening. Rápido y ligero."""
    stock = yf.Ticker(ticker)
    info = stock.info

    if not info or not info.get("marketCap"):
        return None

    return {
        "ticker": ticker,
        "name": info.get("shortName") or ticker,
        "sector": info.get("sector", "N/A"),
        "market_cap": info.get("marketCap"),
        "pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "pb": info.get("priceToBook"),
        "current_ratio": info.get("currentRatio"),
        "de": info.get("debtToEquity"),
        "roic": _calc_roic(info),
        "fcf_yield": _calc_fcf_yield(info),
        "dividend_yield": info.get("dividendYield"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
    }


def _passes_filters(data: dict, filters: dict) -> bool:
    """Aplica los filtros cuantitativos. True si pasa todos."""
    checks = {
        "pe_ratio_max": ("pe", lambda v, f: v <= f),
        "pb_ratio_max": ("pb", lambda v, f: v <= f),
        "current_ratio_min": ("current_ratio", lambda v, f: v >= f),
        "debt_to_equity_max": ("de", lambda v, f: v <= f * 100),  # yfinance en %
        "market_cap_min": ("market_cap", lambda v, f: v >= f),
        "fcf_yield_min": ("fcf_yield", lambda v, f: v >= f),
        "roic_min": ("roic", lambda v, f: v >= f),
    }

    for filter_key, (data_key, check_fn) in checks.items():
        if filter_key not in filters:
            continue
        val = data.get(data_key)
        if val is None:
            continue  # Si no hay dato, no penalizar
        if not check_fn(val, filters[filter_key]):
            return False

    # Filtro compuesto P/E × P/B
    if "pe_times_pb_max" in filters:
        pe = data.get("pe")
        pb = data.get("pb")
        if pe and pb and (pe * pb) > filters["pe_times_pb_max"]:
            return False

    return True


def _calc_score(data: dict, filters: dict) -> float:
    """
    Score simple para rankear candidatas. Mayor = mejor.
    Combina yield, bajo PE y rentabilidad.
    """
    score = 0
    if data.get("fcf_yield"):
        score += data["fcf_yield"] * 100    # 8% FCF yield = +8 puntos
    if data.get("pe") and data["pe"] > 0:
        score += max(0, 20 - data["pe"])    # PE=8 → +12 puntos; PE=15 → +5
    if data.get("pb") and data["pb"] > 0:
        score += max(0, 3 - data["pb"])     # PB=0.8 → +2.2 puntos
    if data.get("dividend_yield"):
        score += data["dividend_yield"] * 50
    return round(score, 2)


def _calc_fcf_yield(info: dict) -> float | None:
    """Estima FCF yield = FCF / Market Cap."""
    fcf = info.get("freeCashflow")
    mcap = info.get("marketCap")
    if fcf and mcap and mcap > 0:
        return round(fcf / mcap, 4)
    return None


def _calc_roic(info: dict) -> float | None:
    """Estima ROIC = NOPAT / capital invertido (deuda + equity - cash).

    Usa operatingMargins × revenue como proxy de EBIT, tax rate 21% (corp USA).
    Devuelve None si faltan inputs imprescindibles.
    """
    revenue = info.get("totalRevenue")
    op_margin = info.get("operatingMargins")
    debt = info.get("totalDebt") or 0
    cash = info.get("totalCash") or 0
    shares = info.get("sharesOutstanding")
    book_value_ps = info.get("bookValue")

    if not (revenue and op_margin and shares and book_value_ps):
        return None

    ebit = revenue * op_margin
    nopat = ebit * (1 - 0.21)
    equity = book_value_ps * shares
    invested = debt + equity - cash
    if invested <= 0:
        return None
    return round(nopat / invested, 4)


def _load_filters(filter_name: str) -> dict:
    with open(FILTERS_FILE) as f:
        all_filters = yaml.safe_load(f)
    return all_filters.get(filter_name, {})
