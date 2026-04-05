"""
Actualiza el Excel de valoración con escenarios reales decididos por Opus.

Uso:
    python tools/update_excel.py DE scenarios.json

Donde scenarios.json tiene la estructura:
{
    "bear": {
        "revenue_growth_y1": -0.05, "revenue_growth_y2": 0.03, "revenue_growth_y3": 0.05,
        "revenue_growth_y4": 0.05, "revenue_growth_y5": 0.03,
        "gross_margin": 0.345, "sga_pct": 0.085, "rd_pct": 0.043,
        "da_pct": 0.04, "capex_pct": 0.085, "tax_rate": 0.19,
        "wacc": 0.105, "terminal_multiple": 11
    },
    "base": { ... },
    "bull": { ... }
}

Regenera el Excel completo con los escenarios proporcionados.
"""

import json
import sys
import argparse
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import VALUATIONS_DIR
from tools.financial_data import get_company_data, extract_historical_data, extract_metrics
from tools.excel_generator import generate_valuation_excel


def update_excel(ticker: str, scenarios: dict):
    """Regenera el Excel con escenarios reales."""
    folder = ticker.replace(".", "_")
    output_dir = VALUATIONS_DIR / folder

    if not output_dir.exists():
        print(f"Error: no existe carpeta para {ticker}. Ejecuta primero: python main.py --analyst {ticker}")
        sys.exit(1)

    # Validar que los 3 escenarios existen
    for sc_name in ["bear", "base", "bull"]:
        if sc_name not in scenarios:
            print(f"Error: falta escenario '{sc_name}' en el JSON")
            sys.exit(1)
        sc = scenarios[sc_name]
        required = ["revenue_growth_y1", "gross_margin", "sga_pct", "wacc", "terminal_multiple"]
        missing = [k for k in required if k not in sc]
        if missing:
            print(f"Error: escenario '{sc_name}' le faltan campos: {missing}")
            sys.exit(1)

    # Cargar datos financieros (usa caché)
    print(f"  Cargando datos de {ticker}...")
    data = get_company_data(ticker)
    historical = extract_historical_data(data)
    metrics = extract_metrics(data, historical)

    # Generar Excel con escenarios reales
    excel_path = str(output_dir / f"{folder}_modelo_valoracion.xlsx")
    _generate_with_scenarios(ticker, data, historical, metrics, scenarios, excel_path)

    print(f"\n  Excel actualizado: {excel_path}")
    print(f"  Escenarios:")
    for name in ["bear", "base", "bull"]:
        sc = scenarios[name]
        print(f"    {name.capitalize():5s}: WACC={sc['wacc']:.1%}, TV={sc['terminal_multiple']:.0f}x, "
              f"Growth Y1={sc['revenue_growth_y1']:.1%}, GM={sc['gross_margin']:.1%}")


def _generate_with_scenarios(ticker, data, historical, metrics, real_scenarios, excel_path):
    """Llama a generate_valuation_excel inyectando los escenarios reales."""
    from tools.excel_generator import generate_valuation_excel as _gen

    # Monkey-patch: guardamos los escenarios reales en metrics para que
    # generate_valuation_excel los use en vez de construir placeholders.
    # Esto es un hack temporal — idealmente refactorizar la función.
    metrics["_real_scenarios"] = real_scenarios

    _gen(ticker, data, historical, metrics, excel_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Actualizar Excel con escenarios reales")
    parser.add_argument("ticker", help="Ticker (ej: DE, AAPL)")
    parser.add_argument("scenarios_file", help="Path al JSON con escenarios bear/base/bull")
    args = parser.parse_args()

    with open(args.scenarios_file, encoding="utf-8") as f:
        scenarios = json.load(f)

    update_excel(args.ticker, scenarios)
