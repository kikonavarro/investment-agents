"""
Módulo para descargar filings 10-K desde SEC EDGAR.
Usa la API EDGAR full-text search y descarga los documentos HTML.
"""

import os
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "ValoracionEmpresas/1.0 (contacto@valoracion.com)",
    "Accept-Encoding": "gzip, deflate",
}

EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{cik}%22&dateRange=custom&startdt={start}&enddt={end}&forms=10-K"
EDGAR_COMPANY_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_FILING_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=include&count=5&search_text=&action=getcompany"


def get_cik(ticker: str) -> str:
    """Obtiene el CIK number de una empresa a partir del ticker."""
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=10-K&dateRange=custom&startdt=2020-01-01&enddt=2026-12-31"
    # Método alternativo más fiable: usar el endpoint de tickers
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(tickers_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            cik = str(entry["cik_str"]).zfill(10)
            return cik

    raise ValueError(f"No se encontró CIK para ticker: {ticker}")


def get_10k_filings(cik: str, num_filings: int = 3) -> list:
    """
    Obtiene las URLs de los últimos 10-K filings desde SEC EDGAR.
    Retorna lista de dicts con: accession_number, filing_date, primary_doc_url
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    filings = []
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form == "10-K" and len(filings) < num_filings:
            accession = accessions[i].replace("-", "")
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{primary_docs[i]}"
            filings.append({
                "accession_number": accessions[i],
                "filing_date": dates[i],
                "primary_doc_url": doc_url,
                "year": dates[i][:4],
            })

    return filings


def download_filing(filing: dict, output_dir: str) -> str:
    """Descarga un filing individual y lo guarda como HTML."""
    url = filing["primary_doc_url"]
    year = filing["year"]

    os.makedirs(output_dir, exist_ok=True)

    # Determinar extensión del archivo
    ext = ".html"
    if url.endswith(".htm"):
        ext = ".htm"

    filepath = os.path.join(output_dir, f"10K_{year}{ext}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(resp.content)

        print(f"  ✓ Descargado 10-K {year}: {filepath}")
        return filepath
    except Exception as e:
        print(f"  ✗ Error descargando 10-K {year}: {e}")
        return None


def download_10k_filings(ticker: str, output_dir: str = None, num_filings: int = 3) -> list:
    """
    Función principal: descarga los últimos N 10-K filings de una empresa.

    Args:
        ticker: Ticker de la empresa (ej: AAPL)
        output_dir: Directorio de salida (default: {ticker}/SEC_filings/)
        num_filings: Número de filings a descargar (default: 3)

    Returns:
        Lista de paths de archivos descargados
    """
    if output_dir is None:
        output_dir = os.path.join(ticker, "SEC_filings")

    print(f"\n📄 Descargando 10-K filings para {ticker}...")

    # Obtener CIK
    try:
        cik = get_cik(ticker)
        print(f"  CIK encontrado: {cik}")
    except Exception as e:
        print(f"  Error obteniendo CIK: {e}")
        return []

    # Obtener lista de filings
    time.sleep(0.5)  # Rate limiting SEC
    try:
        filings = get_10k_filings(cik, num_filings)
        print(f"  Encontrados {len(filings)} filings 10-K")
    except Exception as e:
        print(f"  Error obteniendo lista de filings: {e}")
        return []

    # Descargar cada filing
    downloaded = []
    for filing in filings:
        time.sleep(0.5)  # Rate limiting SEC
        path = download_filing(filing, output_dir)
        if path:
            downloaded.append(path)

    return downloaded


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    download_10k_filings(ticker)
