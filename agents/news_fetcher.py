"""
News Fetcher Agent — obtiene noticias recientes de un ticker y las devuelve
formateadas para que otros agentes (social_media, content_writer) las consuman.

No usa Claude: es puro Python (fetch RSS + formateo).
"""
from tools.news_fetcher import get_ticker_news, format_news_for_llm


def run_news_fetcher(ticker: str, max_items: int = 5) -> dict:
    """
    Descarga noticias recientes y devuelve dict consumible por otros agentes.

    Returns:
        {
            "ticker": "ASTS",
            "news_count": 4,
            "news_formatted": "ASTS | Noticias recientes (4)\n...",
            "news_items": [{"title": ..., "date": ..., "summary": ...}, ...]
        }
    """
    print(f"  [news_fetcher] Buscando noticias de {ticker}...")
    items = get_ticker_news(ticker, max_items=max_items)
    formatted = format_news_for_llm(items, ticker)

    return {
        "ticker": ticker,
        "news_count": len(items),
        "news_formatted": formatted,
        "news_items": items,
    }
