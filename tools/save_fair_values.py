"""
Guarda fair values de Opus en history.json.

Uso:
    python tools/save_fair_values.py TICKER --bear 380 --base 540 --bull 750
    python tools/save_fair_values.py DE --bear 380 --base 540 --bull 750

Actualiza el último entry de history.json con los fair values.
Si no hay entry para hoy, crea uno nuevo.
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

VALUATIONS_DIR = Path(__file__).parent.parent / "data" / "valuations"


def save_fair_values(ticker: str, bear: float, base: float, bull: float):
    """Guarda fair values en history.json del ticker."""
    folder = ticker.replace(".", "_")
    history_path = VALUATIONS_DIR / folder / "history.json"

    if not history_path.parent.exists():
        print(f"Error: no existe carpeta para {ticker} en {history_path.parent}")
        sys.exit(1)

    history = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            history = []

    today = datetime.now().strftime("%Y-%m-%d")

    # Buscar entry de hoy o el último
    target = None
    for entry in reversed(history):
        if entry.get("date") == today:
            target = entry
            break

    if target is None and history:
        # Actualizar el último entry existente
        target = history[-1]

    if target is None:
        # Crear entry mínimo
        target = {"date": today, "current_price": 0, "currency": "$"}
        history.append(target)

    target["fair_value_bear"] = bear
    target["fair_value_base"] = base
    target["fair_value_bull"] = bull
    target["fair_value_weighted"] = round(0.4 * bear + 0.4 * base + 0.2 * bull, 2)

    history_path.write_text(
        json.dumps(history, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )

    weighted = target["fair_value_weighted"]
    price = target.get("current_price", 0)
    mos = f"{(weighted - price) / weighted * 100:.1f}%" if weighted > 0 and price > 0 else "N/A"

    print(f"  Fair values guardados para {ticker}:")
    print(f"    Bear: ${bear:,.2f} | Base: ${base:,.2f} | Bull: ${bull:,.2f}")
    print(f"    Ponderado (40/40/20): ${weighted:,.2f}")
    if price > 0:
        print(f"    Precio: ${price:,.2f} | MoS: {mos}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Guardar fair values en history.json")
    parser.add_argument("ticker", help="Ticker (ej: DE, AAPL, ITX.MC)")
    parser.add_argument("--bear", type=float, required=True, help="Fair value escenario bear")
    parser.add_argument("--base", type=float, required=True, help="Fair value escenario base")
    parser.add_argument("--bull", type=float, required=True, help="Fair value escenario bull")
    args = parser.parse_args()

    save_fair_values(args.ticker, args.bear, args.base, args.bull)
