"""
Watchlist / loop cerrado — cruza los fair values guardados (history.json) con el
precio VIVO de mercado y clasifica cada tesis por margen de seguridad, para flag de
oportunidades de compra/venta AHORA.

Es el primer eslabón del "loop cerrado": Opus escribe tesis con fair value → aquí se
vigila el precio contra ese fair value → se actúa cuando hay margen.

Diseño: la lógica de cruce y clasificación es PURA y testeable (`evaluate`, `scan`).
El precio vivo (`fetch_live_prices`) se aísla en una función con red (yahooquery
batched, una sola llamada para todos los tickers). No opera ni toca las tesis; lo
único que escribe es el log append-only de snapshots (track record, ver abajo).
"""

import json
from datetime import date
from pathlib import Path

from tools.signals import classify_signal

# Umbrales de acción (coherentes con las bandas de signals.classify_signal y con la
# filosofía value: exigir margen de seguridad para comprar).
BUY_MOS = 25.0    # MoS >= 25% → zona de compra
SELL_MOS = -25.0  # MoS <= -25% → zona de venta / evitar

# Si el MoS ya era extremo en la PROPIA finalización (FV vs precio de entonces), el fair
# value/método es sospechoso: o la tesis está obsoleta, o usó un método equivocado (p. ej.
# DCF simple sobre Tesla, que pide SoP). Distinto de una oportunidad real por caída reciente
# (ahí el precio se movió DESPUÉS de la tesis, no estaba extremo al escribirla).
SUSPECT_MOS_ORIGIN = 50.0


def evaluate(fv: dict, live_price: float) -> dict:
    """Evalúa una posición contra su fair value guardado. PURO.

    fv = {bear, base, bull, weighted, saved_price, currency, date}.
    MoS = (fair_value_ponderado - precio) / fair_value_ponderado. Triggers de suelo
    (precio <= bear, por debajo del peor caso) y techo (precio >= bull)."""
    weighted = fv.get("weighted") or 0
    bear = fv.get("bear") or 0
    bull = fv.get("bull") or 0
    saved = fv.get("saved_price") or 0
    change = (live_price - saved) / saved * 100 if saved > 0 else None
    row = {
        "live_price": live_price,
        "weighted": weighted,
        "saved_price": saved,
        "price_change_pct": change,
        "currency": fv.get("currency", "$"),
        "date": fv.get("date"),
    }

    # Fair value ponderado <= 0: la tesis no se valoró por este DCF (pre-profit por
    # EV/Revenue, minera por NAV, SoP...) o los datos hay que revisarlos. Un MoS sobre
    # un FV <= 0 no significa nada: se marca N/A en vez de un engañoso "VALOR JUSTO".
    if weighted <= 0:
        row.update({"mos": 0.0, "emoji": "❓", "action": "NA",
                    "label": "N/A (FV ≤ 0 — método no-DCF o revisar)",
                    "below_bear": False, "above_bull": False,
                    "mos_origin": None, "suspect": False})
        return row

    mos = (weighted - live_price) / weighted * 100
    emoji, label, _ = classify_signal(mos)
    # MoS en la finalización (FV vs precio de entonces): si ya era extremo, el FV/método
    # es sospechoso (obsoleto o equivocado), no una oportunidad por caída reciente.
    mos_origin = (weighted - saved) / weighted * 100 if saved > 0 else None
    row.update({
        "mos": mos,
        "emoji": emoji,
        "label": label,
        "action": "BUY" if mos >= BUY_MOS else ("SELL" if mos <= SELL_MOS else "HOLD"),
        "below_bear": bool(bear and live_price <= bear),  # suelo: por debajo del bear
        "above_bull": bool(bull and live_price >= bull),  # techo: por encima del bull
        "mos_origin": mos_origin,
        "suspect": mos_origin is not None and abs(mos_origin) >= SUSPECT_MOS_ORIGIN,
    })
    return row


def scan(saved: dict, prices: dict) -> list:
    """Cruza fair values guardados con precios vivos. PURO. Devuelve filas ordenadas
    por MoS descendente (las más infravaloradas — mejores compras — primero). Omite
    tickers sin precio vivo (no aparecen en `prices`)."""
    rows = []
    for ticker, fv in saved.items():
        price = prices.get(ticker)
        if not price or price <= 0:
            continue
        row = evaluate(fv, price)
        row["ticker"] = ticker
        rows.append(row)
    rows.sort(key=lambda r: r["mos"], reverse=True)
    return rows


def load_saved_fair_values(valuations_dir=None) -> dict:
    """Lee el último fair value guardado de cada history.json. Devuelve
    {ticker: {bear, base, bull, weighted, saved_price, currency, date}}.
    `ticker` es el nombre de carpeta (MC_PA), no el de Yahoo (MC.PA)."""
    if valuations_dir is None:
        from config.settings import VALUATIONS_DIR
        valuations_dir = VALUATIONS_DIR
    out = {}
    for hp in sorted(Path(valuations_dir).glob("*/history.json")):
        try:
            history = json.loads(hp.read_text(encoding="utf-8"))
        except Exception:
            continue
        entry = next((e for e in reversed(history) if e.get("fair_value_base")), None)
        if not entry:
            continue
        bear = entry.get("fair_value_bear") or 0
        base = entry.get("fair_value_base") or 0
        bull = entry.get("fair_value_bull") or 0
        weighted = entry.get("fair_value_weighted") or (0.4 * bear + 0.4 * base + 0.2 * bull)
        out[hp.parent.name] = {
            "bear": bear, "base": base, "bull": bull, "weighted": weighted,
            "saved_price": entry.get("current_price") or 0,
            "currency": entry.get("currency", "$"),
            "date": entry.get("date"),
        }
    return out


def fetch_live_prices(tickers: list) -> dict:
    """Precio vivo de mercado, en UNA sola llamada batched (yahooquery). Tolerante a
    errores: los tickers sin precio simplemente no aparecen en el dict devuelto.
    Mapea el nombre de carpeta (MC_PA) al de Yahoo (MC.PA) y devuelve con la clave
    de carpeta para casar con `load_saved_fair_values`."""
    if not tickers:
        return {}
    from yahooquery import Ticker
    from tools.financial_data import _to_yahoo_ticker

    yahoo_map = {_to_yahoo_ticker(t): t for t in tickers}  # yahoo → folder
    out = {}
    try:
        data = Ticker(list(yahoo_map.keys()), asynchronous=False).price
    except Exception:
        return out
    if not isinstance(data, dict):
        return out
    for yt, folder in yahoo_map.items():
        info = data.get(yt)
        if isinstance(info, dict):
            price = info.get("regularMarketPrice")
            if isinstance(price, (int, float)) and price > 0:
                out[folder] = float(price)
    return out


def append_snapshot(rows: list, path=None) -> tuple:
    """Acumula el escaneo de hoy en un log append-only (JSONL) — la materia prima del
    track record (#7 del roadmap): con snapshots en el tiempo se puede medir hit-rate
    (¿las infravaloradas subieron, las sobrevaloradas bajaron?) y calibrar sesgos
    sistemáticos de las tesis (¿los bull son siempre demasiado optimistas?).

    Una línea JSON por tesis escaneada. Idempotente por día y ticker: re-ejecutar el
    scan el mismo día no duplica líneas. Devuelve (path, nº de líneas nuevas)."""
    if path is None:
        from config.settings import DATA_DIR
        path = DATA_DIR / "watchlist_snapshots.jsonl"
    path = Path(path)
    today = date.today().isoformat()

    ya_logueados = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue  # línea corrupta: se ignora, no rompe el scan
            if e.get("date") == today:
                ya_logueados.add(e.get("ticker"))

    nuevos = 0
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            if r["ticker"] in ya_logueados:
                continue
            f.write(json.dumps({
                "date": today,
                "ticker": r["ticker"],
                "price": r["live_price"],
                "fv_weighted": r["weighted"],
                "mos": round(r["mos"], 2),
                "action": r["action"],
                "suspect": bool(r.get("suspect")),
                "thesis_date": r.get("date"),
            }, ensure_ascii=False) + "\n")
            nuevos += 1
    return path, nuevos


def run_scan() -> list:
    """Orquesta el escaneo completo (con red): carga fair values + precio vivo + cruza."""
    saved = load_saved_fair_values()
    prices = fetch_live_prices(list(saved.keys()))
    return scan(saved, prices)
