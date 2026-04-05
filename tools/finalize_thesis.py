"""
Finaliza una tesis: guarda fair values en history.json y regenera el Excel
con los escenarios reales decididos por Opus.

Uso:
    python tools/finalize_thesis.py DE scenarios.json

Donde scenarios.json tiene:
{
    "fair_values": {"bear": 395, "base": 550, "bull": 760},
    "scenarios": {
        "bear": {
            "revenue_growth_y1": -0.05, "revenue_growth_y2": 0.03, ...
            "gross_margin": 0.345, "sga_pct": 0.085, "rd_pct": 0.043,
            "da_pct": 0.04, "capex_pct": 0.085, "tax_rate": 0.19,
            "wacc": 0.105, "terminal_multiple": 11
        },
        "base": { ... },
        "bull": { ... }
    }
}
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import VALUATIONS_DIR


def finalize_thesis(ticker: str, data: dict):
    """Guarda fair values en history.json y regenera Excel con escenarios reales."""
    folder = ticker.replace(".", "_")
    output_dir = VALUATIONS_DIR / folder

    if not output_dir.exists():
        print(f"Error: no existe carpeta para {ticker}")
        sys.exit(1)

    fair_values = data.get("fair_values", {})
    scenarios = data.get("scenarios", {})

    # --- 1. Guardar fair values en history.json ---
    bear = fair_values.get("bear", 0)
    base = fair_values.get("base", 0)
    bull = fair_values.get("bull", 0)

    if not all([bear, base, bull]):
        print("Error: faltan fair_values (bear/base/bull)")
        sys.exit(1)

    weighted = round(0.4 * bear + 0.4 * base + 0.2 * bull, 2)

    history_path = output_dir / "history.json"
    history = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            history = []

    today = datetime.now().strftime("%Y-%m-%d")

    # Buscar entry de hoy
    target = None
    for entry in reversed(history):
        if entry.get("date") == today:
            target = entry
            break

    if target is None and history:
        target = history[-1]

    if target is None:
        target = {"date": today, "current_price": 0, "currency": "$"}
        history.append(target)

    target["fair_value_bear"] = bear
    target["fair_value_base"] = base
    target["fair_value_bull"] = bull
    target["fair_value_weighted"] = weighted

    # Limpiar entries basura (fair values < $1 del pipeline viejo)
    cleaned = 0
    for entry in history:
        for key in ["fair_value_bear", "fair_value_base", "fair_value_bull"]:
            if entry.get(key) and 0 < entry[key] < 1:
                entry.pop(key, None)
                cleaned += 1
        if "fair_value_weighted" in entry:
            fvs = [entry.get(f"fair_value_{s}", 0) or 0 for s in ["bear", "base", "bull"]]
            if any(0 < fv < 1 for fv in fvs):
                entry.pop("fair_value_weighted", None)

    history_path.write_text(
        json.dumps(history, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )

    price = target.get("current_price", 0)
    mos = f"{(weighted - price) / weighted * 100:.1f}%" if weighted > 0 and price > 0 else "N/A"

    print(f"\n  === Tesis finalizada: {ticker} ===")
    print(f"  Fair values guardados:")
    print(f"    Bear: ${bear:,.2f} | Base: ${base:,.2f} | Bull: ${bull:,.2f}")
    print(f"    Ponderado (40/40/20): ${weighted:,.2f}")
    if price > 0:
        print(f"    Precio: ${price:,.2f} | MoS: {mos}")
    if cleaned:
        print(f"  Limpiados {cleaned} fair values basura del pipeline viejo")

    # --- 2. Regenerar Excel con escenarios reales ---
    if scenarios and all(k in scenarios for k in ("bear", "base", "bull")):
        # Validar campos mínimos
        required = ["revenue_growth_y1", "gross_margin", "sga_pct", "wacc", "terminal_multiple"]
        valid = True
        for sc_name in ["bear", "base", "bull"]:
            missing = [k for k in required if k not in scenarios[sc_name]]
            if missing:
                print(f"  [!] Escenario '{sc_name}' le faltan: {missing} — Excel no actualizado")
                valid = False
                break

        if valid:
            from tools.financial_data import get_company_data, extract_historical_data, extract_metrics
            from tools.excel_generator import generate_valuation_excel

            print(f"\n  Regenerando Excel con escenarios reales...")
            yahoo_data = get_company_data(ticker)
            historical = extract_historical_data(yahoo_data)
            metrics = extract_metrics(yahoo_data, historical)
            metrics["_real_scenarios"] = scenarios

            excel_path = str(output_dir / f"{folder}_modelo_valoracion.xlsx")
            generate_valuation_excel(ticker, yahoo_data, historical, metrics, excel_path)

            print(f"  Escenarios:")
            for name in ["bear", "base", "bull"]:
                sc = scenarios[name]
                print(f"    {name.capitalize():5s}: WACC={sc['wacc']:.1%}, "
                      f"TV={sc['terminal_multiple']:.0f}x, "
                      f"Growth Y1={sc['revenue_growth_y1']:.1%}, "
                      f"GM={sc['gross_margin']:.1%}")
    else:
        print(f"\n  Sin escenarios completos — Excel no actualizado")


def clean_all_history():
    """Limpia fair values basura (<$1) de todos los history.json."""
    cleaned_total = 0
    for history_path in VALUATIONS_DIR.glob("*/history.json"):
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        cleaned = 0
        for entry in history:
            for key in ["fair_value_bear", "fair_value_base", "fair_value_bull", "fair_value_weighted"]:
                if entry.get(key) and 0 < entry[key] < 1:
                    entry.pop(key, None)
                    cleaned += 1
            # Limpiar campos legacy que ya no existen
            for legacy_key in ["growth_y1_base", "wacc_base", "tv_base"]:
                entry.pop(legacy_key, None)

        if cleaned:
            history_path.write_text(
                json.dumps(history, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8"
            )
            ticker = history_path.parent.name
            print(f"  {ticker}: {cleaned} valores basura eliminados")
            cleaned_total += cleaned

    print(f"\n  Total: {cleaned_total} valores basura limpiados")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finalizar tesis: fair values + Excel")
    parser.add_argument("ticker", nargs="?", help="Ticker (ej: DE, AAPL)")
    parser.add_argument("data_file", nargs="?", help="JSON con fair_values y scenarios")
    parser.add_argument("--clean-all", action="store_true",
                        help="Limpiar fair values basura de todos los tickers")
    args = parser.parse_args()

    if args.clean_all:
        clean_all_history()
    elif args.ticker and args.data_file:
        with open(args.data_file, encoding="utf-8") as f:
            data = json.load(f)
        finalize_thesis(args.ticker, data)
    else:
        parser.print_help()
