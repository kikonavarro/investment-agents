"""
Módulo para buscar noticias recientes de una empresa.
Usa Yahoo Finance RSS y Google News RSS (sin API key).
"""

import warnings
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from datetime import datetime

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def fetch_news(ticker: str, company_name: str = "", max_news: int = 15) -> list:
    """
    Busca noticias recientes de una empresa.

    Args:
        ticker: Ticker de la empresa
        company_name: Nombre completo de la empresa
        max_news: Número máximo de noticias

    Returns:
        Lista de dicts con: title, source, date, link, summary
    """
    print(f"\n📰 Buscando noticias para {ticker}...")

    all_news = []

    # Fuente 1: Yahoo Finance RSS
    yahoo_news = _fetch_yahoo_finance_news(ticker)
    all_news.extend(yahoo_news)

    # Fuente 2: Google News RSS
    search_term = f"{ticker} stock" if not company_name else f"{company_name} {ticker}"
    google_news = _fetch_google_news(search_term)
    all_news.extend(google_news)

    # Deduplicar por título similar
    seen_titles = set()
    unique_news = []
    for item in all_news:
        title_key = item["title"].lower()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_news.append(item)

    # Ordenar por fecha (más recientes primero)
    unique_news.sort(key=lambda x: x.get("date_sort", ""), reverse=True)

    result = unique_news[:max_news]
    print(f"  Encontradas {len(result)} noticias")
    return result


def _fetch_yahoo_finance_news(ticker: str) -> list:
    """Obtiene noticias desde Yahoo Finance RSS."""
    news = []
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        resp = requests.get(url, headers=HEADERS, timeout=15)

        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.content, "html.parser")
        items = soup.find_all("item")

        for item in items[:10]:
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubdate")
            description = item.find("description")

            title_text = title.text.strip() if title else ""
            if not title_text:
                continue

            date_text = ""
            date_sort = ""
            if pub_date:
                try:
                    dt = datetime.strptime(pub_date.text.strip()[:25], "%a, %d %b %Y %H:%M:%S")
                    date_text = dt.strftime("%Y-%m-%d")
                    date_sort = dt.strftime("%Y%m%d%H%M%S")
                except Exception:
                    date_text = pub_date.text.strip()[:10]
                    date_sort = date_text

            news.append({
                "title": title_text,
                "source": "Yahoo Finance",
                "date": date_text,
                "date_sort": date_sort,
                "link": link.text.strip() if link else "",
                "summary": description.text.strip()[:200] if description else "",
            })

    except Exception as e:
        print(f"  ⚠ Error Yahoo Finance RSS: {e}")

    return news


def _fetch_google_news(search_term: str) -> list:
    """Obtiene noticias desde Google News RSS."""
    news = []
    try:
        import urllib.parse
        query = urllib.parse.quote(search_term)
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(url, headers=HEADERS, timeout=15)

        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.content, "html.parser")
        items = soup.find_all("item")

        for item in items[:10]:
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubdate")
            source_tag = item.find("source")

            title_text = title.text.strip() if title else ""
            if not title_text:
                continue

            source = source_tag.text.strip() if source_tag else "Google News"

            date_text = ""
            date_sort = ""
            if pub_date:
                try:
                    dt = datetime.strptime(pub_date.text.strip()[:25], "%a, %d %b %Y %H:%M:%S")
                    date_text = dt.strftime("%Y-%m-%d")
                    date_sort = dt.strftime("%Y%m%d%H%M%S")
                except Exception:
                    date_text = pub_date.text.strip()[:10]
                    date_sort = date_text

            news.append({
                "title": title_text,
                "source": source,
                "date": date_text,
                "date_sort": date_sort,
                "link": link.text.strip() if link else "",
                "summary": "",
            })

    except Exception as e:
        print(f"  ⚠ Error Google News RSS: {e}")

    return news


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    news = fetch_news(ticker, "Apple Inc")
    for n in news:
        print(f"  [{n['date']}] {n['title']} ({n['source']})")
