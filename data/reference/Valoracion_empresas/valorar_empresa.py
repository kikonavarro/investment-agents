#!/usr/bin/env python3
"""
Sistema Automatizado de Valoración de Empresas
===============================================
Genera un modelo de valoración completo (Excel + PDF) para cualquier
empresa pública a partir de su ticker.

Soporta:
    - EEUU: AAPL, MSFT, GOOGL
    - Australia (ASX): WHC.AX, YAL.AX, SMR.AX
    - Cualquier mercado soportado por yfinance

Uso:
    python3 valorar_empresa.py AAPL
    python3 valorar_empresa.py WHC.AX
    python3 valorar_empresa.py WHC.AX YAL.AX SMR.AX  (múltiples)

Output:
    {ticker}/
    ├── SEC_filings/          # 10-K filings (solo EEUU)
    ├── {ticker}_modelo_valoracion.xlsx
    └── {ticker}_tesis_inversion.pdf
"""

import sys
import os
import time
from datetime import datetime


def _is_us_ticker(ticker: str) -> bool:
    """Determina si un ticker es de EEUU (sin sufijo de exchange)."""
    return "." not in ticker


def _clean_ticker_for_folder(ticker: str) -> str:
    """Limpia el ticker para usarlo como nombre de carpeta."""
    return ticker.replace(".", "_")


def _get_currency_symbol(ticker: str) -> str:
    """Retorna el símbolo de moneda según el exchange."""
    if ticker.endswith(".AX"):
        return "A$"
    elif ticker.endswith(".L"):
        return "£"
    elif ticker.endswith(".TO") or ticker.endswith(".V"):
        return "C$"
    return "$"


def main():
    # ============================================================
    # Parsear argumentos
    # ============================================================
    if len(sys.argv) < 2:
        print("=" * 60)
        print("  Sistema Automatizado de Valoración de Empresas")
        print("=" * 60)
        print("\nUso: python3 valorar_empresa.py <TICKER> [TICKER2] [TICKER3]")
        print("\nEjemplos:")
        print("  python3 valorar_empresa.py AAPL")
        print("  python3 valorar_empresa.py WHC.AX YAL.AX SMR.AX")
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]

    for ticker in tickers:
        try:
            run_valuation(ticker)
        except Exception as e:
            print(f"\n❌ Error valorando {ticker}: {e}")
            import traceback
            traceback.print_exc()

        if len(tickers) > 1:
            print("\n" + "=" * 60)
            print(f"  Esperando 5s antes del siguiente ticker...")
            print("=" * 60)
            time.sleep(5)


def run_valuation(ticker: str):
    """Ejecuta la valoración completa para un ticker."""
    folder_name = _clean_ticker_for_folder(ticker)
    currency = _get_currency_symbol(ticker)
    is_us = _is_us_ticker(ticker)

    print("=" * 60)
    print(f"  Valoración de {ticker}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Crear directorio de output
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder_name)
    os.makedirs(output_dir, exist_ok=True)

    start_time = time.time()
    downloaded_files = []

    # ============================================================
    # PASO A: Descargar filings (solo EEUU - SEC EDGAR)
    # ============================================================
    if is_us:
        print("\n" + "─" * 40)
        print("PASO 1/5: Descarga de 10-K (SEC EDGAR)")
        print("─" * 40)

        try:
            from sec_downloader import download_10k_filings
            sec_dir = os.path.join(output_dir, "SEC_filings")
            downloaded_files = download_10k_filings(ticker, sec_dir)
            print(f"  → {len(downloaded_files)} filings descargados")
        except Exception as e:
            print(f"  ⚠ Error descargando SEC filings: {e}")
            print("  → Continuando sin filings SEC...")
    else:
        print("\n" + "─" * 40)
        print("PASO 1/5: Filings regulatorios")
        print("─" * 40)
        print(f"  → Ticker internacional ({ticker}): SEC EDGAR no aplica")
        print(f"  → Datos financieros se obtienen de yfinance")

    # ============================================================
    # PASO B: Obtener datos financieros
    # ============================================================
    print("\n" + "─" * 40)
    print("PASO 2/5: Datos financieros (yfinance)")
    print("─" * 40)

    from financial_data import get_company_data, extract_historical_data, generate_scenarios

    data = get_company_data(ticker)
    historical = extract_historical_data(data)
    scenarios = generate_scenarios(data, historical)

    company_name = data["info"].get("longName", ticker)
    current_price = data["current_price"]

    print(f"\n  Resumen:")
    print(f"  → Empresa: {company_name}")
    print(f"  → Precio actual: {currency}{current_price:,.2f}")
    print(f"  → Años históricos: {sorted(historical.keys())}")
    print(f"  → Segmentos: {[s['name'] for s in data['segments']]}")
    for k, v in scenarios.items():
        print(f"  → {k.capitalize()}: Growth Y1={v['revenue_growth_y1']:.1%}, "
              f"WACC={v['wacc']:.1%}, TV={v['terminal_multiple']:.0f}x")

    # ============================================================
    # PASO C: Buscar noticias
    # ============================================================
    print("\n" + "─" * 40)
    print("PASO 3/5: Noticias recientes")
    print("─" * 40)

    try:
        from news_fetcher import fetch_news
        news = fetch_news(ticker, company_name)
    except Exception as e:
        print(f"  ⚠ Error buscando noticias: {e}")
        news = []

    # ============================================================
    # PASO D: Generar Excel de valoración
    # ============================================================
    print("\n" + "─" * 40)
    print("PASO 4/5: Generación del modelo Excel")
    print("─" * 40)

    from excel_generator import generate_valuation_excel

    excel_path = os.path.join(output_dir, f"{folder_name}_modelo_valoracion.xlsx")
    generate_valuation_excel(ticker, data, historical, scenarios, excel_path)

    # ============================================================
    # PASO E: Generar PDF de tesis de inversión
    # ============================================================
    print("\n" + "─" * 40)
    print("PASO 5/5: Generación del PDF de tesis")
    print("─" * 40)

    from pdf_generator import generate_investment_pdf

    pdf_path = os.path.join(output_dir, f"{folder_name}_tesis_inversion.pdf")
    generate_investment_pdf(ticker, data, historical, scenarios, news, pdf_path)

    # ============================================================
    # RESUMEN FINAL
    # ============================================================
    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"  VALORACIÓN COMPLETADA: {company_name} ({ticker})")
    print("=" * 60)
    print(f"\n  Tiempo total: {elapsed:.1f} segundos")
    print(f"\n  Archivos generados:")
    print(f"  📁 {output_dir}/")

    if downloaded_files:
        print(f"  ├── SEC_filings/ ({len(downloaded_files)} filings)")

    print(f"  ├── {folder_name}_modelo_valoracion.xlsx")
    print(f"  └── {folder_name}_tesis_inversion.pdf")

    print(f"\n  Precio actual: {currency}{current_price:,.2f}")
    print(f"  WACC (Base): {scenarios['base']['wacc']:.1%}")
    print(f"  TV Multiple (Base): {scenarios['base']['terminal_multiple']:.0f}x")
    print()


if __name__ == "__main__":
    main()
