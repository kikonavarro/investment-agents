"""
Descarga de filings 10-K desde SEC EDGAR.
Solo aplica a empresas de EEUU (tickers sin sufijo de exchange).
"""

import os
import time
import requests

HEADERS = {
    "User-Agent": "InvestmentAgents/1.0 (contacto@valoracion.com)",
    "Accept-Encoding": "gzip, deflate",
}


def get_cik(ticker: str) -> str:
    """Obtiene el CIK number de una empresa a partir del ticker."""
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(tickers_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            return str(entry["cik_str"]).zfill(10)

    raise ValueError(f"No se encontro CIK para ticker: {ticker}")


def get_10k_filings(cik: str, num_filings: int = 3) -> list:
    """
    Obtiene las URLs de los ultimos 10-K filings desde SEC EDGAR.
    Retorna lista de dicts con: accession_number, filing_date, primary_doc_url, year
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
            doc_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{cik.lstrip('0')}/{accession}/{primary_docs[i]}"
            )
            filings.append({
                "accession_number": accessions[i],
                "filing_date": dates[i],
                "primary_doc_url": doc_url,
                "year": dates[i][:4],
            })

    return filings


def download_filing(filing: dict, output_dir: str) -> str | None:
    """Descarga un filing individual y lo guarda como HTML."""
    url = filing["primary_doc_url"]
    year = filing["year"]

    os.makedirs(output_dir, exist_ok=True)
    ext = ".htm" if url.endswith(".htm") else ".html"
    filepath = os.path.join(output_dir, f"10K_{year}{ext}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
        print(f"    Descargado 10-K {year}: {os.path.basename(filepath)}")
        return filepath
    except Exception as e:
        print(f"    Error descargando 10-K {year}: {e}")
        return None


def download_10k_filings(ticker: str, output_dir: str, num_filings: int = 3) -> list:
    """
    Descarga los ultimos N 10-K filings de una empresa.

    Args:
        ticker: Ticker de la empresa (ej: AAPL)
        output_dir: Directorio de salida
        num_filings: Numero de filings a descargar (default: 3)

    Returns:
        Lista de paths de archivos descargados
    """
    print(f"  [sec] Descargando 10-K filings para {ticker}...")

    try:
        cik = get_cik(ticker)
        print(f"    CIK: {cik}")
    except Exception as e:
        print(f"    Error obteniendo CIK: {e}")
        return []

    time.sleep(0.5)
    try:
        filings = get_10k_filings(cik, num_filings)
        print(f"    Encontrados {len(filings)} filings 10-K")
    except Exception as e:
        print(f"    Error obteniendo lista de filings: {e}")
        return []

    downloaded = []
    for filing in filings:
        time.sleep(0.5)
        path = download_filing(filing, output_dir)
        if path:
            downloaded.append(path)

    return downloaded
