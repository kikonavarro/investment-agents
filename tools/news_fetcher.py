"""
News Fetcher — obtiene noticias recientes de empresas via RSS.
Sin APIs de pago. Fuentes: Yahoo Finance RSS + Google News RSS.
Output comprimido para Claude (~300 tokens max por empresa).
"""
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; investment-agent/1.0)"}


def get_ticker_news(ticker: str, max_items: int = 10) -> list[dict]:
    """
    Obtiene las ultimas noticias de un ticker desde Yahoo Finance + Google News RSS.
    Deduplica por titulo y ordena por fecha.
    """
    all_news = []

    # Yahoo Finance RSS
    yahoo_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    all_news.extend(_fetch_rss(yahoo_url, max_items, "Yahoo Finance"))

    if not all_news:
        base_ticker = ticker.split(".")[0]
        yahoo_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={base_ticker}&region=US&lang=en-US"
        all_news.extend(_fetch_rss(yahoo_url, max_items, "Yahoo Finance"))

    # Google News RSS
    query = urllib.parse.quote(f"{ticker} stock")
    google_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    all_news.extend(_fetch_rss(google_url, max_items, "Google News"))

    # Deduplicar
    seen = set()
    unique = []
    for item in all_news:
        key = item["title"].lower()[:50]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # Ordenar por fecha
    unique.sort(key=lambda x: x.get("date_sort", ""), reverse=True)
    return unique[:max_items]


def fetch_news(ticker: str, company_name: str = "", max_news: int = 15) -> list[dict]:
    """Alias compatible con el sistema de valoracion."""
    return get_ticker_news(ticker, max_news)


def format_news_for_llm(news_items: list[dict], ticker: str) -> str:
    """Comprime noticias recientes a formato minimo para Claude."""
    if not news_items:
        return f"{ticker} | Sin noticias recientes disponibles"

    lines = [f"{ticker} | Noticias recientes ({len(news_items)})"]
    for item in news_items:
        date_str = item.get("date", "")[:10]
        title = item.get("title", "")[:100]
        snippet = item.get("summary", "")[:80].replace("\n", " ")
        if snippet:
            lines.append(f"[{date_str}] {title} -- \"{snippet}...\"")
        else:
            lines.append(f"[{date_str}] {title}")

    return "\n".join(lines)


def get_multi_ticker_news(tickers: list[str], max_per_ticker: int = 3) -> dict[str, list[dict]]:
    """Obtiene noticias para multiples tickers."""
    return {ticker: get_ticker_news(ticker, max_per_ticker) for ticker in tickers}


def _fetch_rss(url: str, max_items: int, source_name: str = "RSS") -> list[dict]:
    """Descarga y parsea un feed RSS."""
    try:
        req = Request(url, headers=_HEADERS)
        with urlopen(req, timeout=10) as resp:
            content = resp.read()
        return _parse_rss(content, max_items, source_name)
    except (URLError, ET.ParseError, Exception):
        return []


def _parse_rss(content: bytes, max_items: int, source_name: str) -> list[dict]:
    """Parsea XML RSS y extrae title, pubDate, description."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []

    items = []
    for item in root.iter("item"):
        title = _text(item, "title")
        pub_date = _text(item, "pubDate")
        description = _text(item, "description")
        link = _text(item, "link")
        source_tag = item.find("source")

        if not title:
            continue

        actual_source = source_tag.text.strip() if source_tag is not None and source_tag.text else source_name
        date_str, date_sort = _parse_date(pub_date)

        items.append({
            "title": _clean_html(title),
            "date": date_str,
            "date_sort": date_sort,
            "summary": _clean_html(description)[:200] if description else "",
            "url": link or "",
            "source": actual_source,
        })

        if len(items) >= max_items:
            break

    return items


def _text(elem, tag: str) -> str:
    child = elem.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#\d+;", "", text)
    return text.strip()


def _parse_date(date_str: str) -> tuple[str, str]:
    """Convierte fecha RSS a (date_display, date_sort)."""
    if not date_str:
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d"), now.strftime("%Y%m%d%H%M%S")
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip()[:25], fmt)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%Y%m%d%H%M%S")
        except ValueError:
            continue
    return date_str[:10], date_str[:10]
