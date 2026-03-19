"""
Screener Engine — filtros cuantitativos sobre universo de acciones.
Todo en Python. Claude no ve los datos crudos, solo el top-15 comprimido.
"""
import yfinance as yf
import yaml
from pathlib import Path

FILTERS_FILE = Path(__file__).parent.parent / "config" / "screener_filters.yaml"

# Universos de tickers (listas pequeñas para no tardar horas)
# En producción puedes ampliar con financedatabase
UNIVERSES = {
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
        "ELE.MC", "NTGY.MC", "MTS.MC", "CABK.MC", "BKIA.MC",
    ],
    "EUROSTOXX600": [
        "NESN.SW", "NOVN.SW", "ROG.SW", "ASML.AS", "MC.PA", "SAP.DE",
        "SIE.DE", "ABI.BR", "AI.PA", "OR.PA", "BNP.PA", "SAN.PA",
        "BATS.L", "GSK.L", "AZN.L", "SHEL.L", "BP.L", "ULVR.L",
        "VOW3.DE", "BMW.DE", "MBG.DE", "BAYN.DE", "ALV.DE",
    ],
}


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

    # Construir universo
    tickers = []
    for market in markets:
        tickers.extend(UNIVERSES.get(market, []))
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
        "roic": None,  # No disponible directamente en yfinance info
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


def _load_filters(filter_name: str) -> dict:
    with open(FILTERS_FILE) as f:
        all_filters = yaml.safe_load(f)
    return all_filters.get(filter_name, {})
