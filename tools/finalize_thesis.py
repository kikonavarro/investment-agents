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
    },
    "_meta": {                          # overrides opcionales (esquema canonico unico)
        "net_debt_override_m": 57.0,    # deuda neta a usar en el DCF, en millones
        "shares_override": 231412113,   # nº de acciones, absoluto (alias antiguo: "shares")
        "revenue_base_m": 1828.0,       # revenue del año 0 de la proyeccion, en millones
        "fv_adjustment": {"pct": 0.10, "reason": "opcionalidad no modelada en el DCF"}
    }                                   # ^ ajuste deliberado sobre el OUTPUT del motor
}

El _meta lo decide Opus y lo respetan POR IGUAL la verificacion del motor y el Excel
(salvo revenue_base en el Excel, pendiente — ver REDISENO). _normalize_meta es la unica
fuente de verdad del esquema y acepta alias historicos para no romper tesis antiguas.
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import VALUATIONS_DIR


def validate_fair_values(bear, base, bull):
    """Valida los fair values oficiales antes de persistirlos. Son el output que va a
    Telegram/Substack: un signo o un orden invertido al teclear publicaría una
    valoración absurda. Devuelve un mensaje de error, o None si son válidos."""
    if not all([bear, base, bull]):
        return "faltan fair_values (bear/base/bull)"
    if bear <= 0 or base <= 0 or bull <= 0:
        return f"los fair values deben ser positivos (bear={bear}, base={base}, bull={bull})"
    if not (bear <= base <= bull):
        return (f"los fair values deben cumplir bear <= base <= bull "
                f"(bear={bear}, base={base}, bull={bull}). ¿Se invirtió algún escenario al teclear?")
    return None


def _run_review_gate(ticker: str, output_dir, folder: str):
    """Ejecuta el reviewer sobre la tesis .md y aborta si hay checks CRÍTICOS.
    Antes el gate dependía de que Opus se acordara de correr el reviewer y respetarlo;
    ahora el único camino a history.json/Excel pasa por aquí (salvo --force)."""
    thesis_path = output_dir / f"{folder}_tesis_inversion.md"
    val_path = output_dir / f"{folder}_valuation.json"
    if not (thesis_path.exists() and val_path.exists()):
        return  # sin tesis o sin datos no hay nada que revisar

    try:
        from tools.thesis_reviewer import review_thesis
        thesis_text = thesis_path.read_text(encoding="utf-8")
        valuation = json.loads(val_path.read_text(encoding="utf-8"))
        review = review_thesis(ticker, thesis_text, valuation)
    except Exception as e:
        # Un bug del reviewer no debe impedir finalizar: avisar y continuar.
        print(f"  [REVIEW GATE] No se pudo ejecutar el reviewer ({e}); se continúa sin bloquear.")
        return

    if review["verdict"] == "FAIL":
        print(f"\n  [REVIEW GATE] FAIL — {review['summary']}")
        for c in review["critical"]:
            print(f"    [CRITICAL] {c['message']}")
        print("\n  Tesis NO finalizada. Corrige los críticos o usa --force para forzar.")
        sys.exit(1)
    elif review["verdict"] == "REVIEW":
        print(f"\n  [REVIEW GATE] {review['summary']} (warnings; se continúa)")
    else:
        print("\n  [REVIEW GATE] PASS")


# Esquema canonico de overrides que una tesis puede declarar en thesis_data["_meta"].
# Opus decide estos valores (juicio); el motor (verificacion) y el Excel los respetan
# por igual, para que un ajuste deliberado no se confunda con un error de calculo.
#   net_debt_override_m : deuda neta a usar en el DCF, en millones (moneda de la empresa).
#   shares_override     : nº de acciones a usar (absoluto, no millones).
#   revenue_base_m      : revenue del año 0 de la proyeccion, en millones.
#   fv_adjustment       : {pct, reason} — ajuste deliberado sobre el OUTPUT del motor
#                         (la tesis se compara contra motor*(1+pct)). Unico que actua
#                         sobre el resultado, no sobre los inputs del DCF.
# Alias historicos aceptados (compatibilidad con tesis ya escritas): "shares" -> shares_override.
def _parse_fv_adjustment(raw):
    """Valida _meta.fv_adjustment = {"pct": <fraccion, p.ej. 0.10>, "reason": "..."}.

    Devuelve {pct, reason} o None si no se declaro o esta mal formado (se ignora sin
    romper). pct es una FRACCION (0.10 = +10%), coherente con el resto de supuestos.
    Se rechaza bool (True/False son int en Python) para no colar pct=1.0 por error."""
    if not isinstance(raw, dict):
        return None
    pct = raw.get("pct")
    if isinstance(pct, bool) or not isinstance(pct, (int, float)):
        return None
    return {"pct": float(pct), "reason": str(raw.get("reason") or "(sin razon declarada)")}


def _normalize_meta(meta: dict | None) -> dict:
    """Normaliza el _meta de la tesis al esquema canonico de overrides del DCF.

    Devuelve SIEMPRE un dict con las tres claves canonicas (valor None si no se
    declararon). Es la unica fuente de verdad del esquema: tanto la verificacion
    como la preparacion del Excel leen los overrides desde aqui, asi que no pueden
    divergir. Acepta alias historicos para no romper las tesis ya guardadas."""
    meta = meta or {}

    def _first(*keys):
        for k in keys:
            v = meta.get(k)
            if v is not None:
                return v
        return None

    return {
        "net_debt_override_m": _first("net_debt_override_m"),
        "shares_override": _first("shares_override", "shares"),
        "revenue_base_m": _first("revenue_base_m"),
        "fv_adjustment": _parse_fv_adjustment(meta.get("fv_adjustment")),
    }


def _dcf_inputs(output_dir, folder: str, meta: dict | None = None):
    """Prepara los inputs de empresa para el motor desde el valuation.json + overrides
    de la tesis (_meta). Devuelve (inputs, info):

      inputs = {revenue, shares, net_debt, pence_factor, price} o None si no aplica.
      info   = {"reason": <por qué no aplica, o None>, "notes": [avisos/correcciones]}

    La RAZÓN siempre se rellena cuando inputs es None: que el motor no verifique nunca
    puede ser silencioso — un caso legítimo (financiera) y un bug (JSON roto) no deben
    parecer lo mismo. Las NOTES dejan rastro de cada heurística/override aplicado."""
    notes = []
    val_path = output_dir / f"{folder}_valuation.json"
    if not val_path.exists():
        return None, {"reason": f"no existe {val_path.name} "
                                f"(genera los datos: python main.py --analyst {folder})",
                      "notes": notes}
    try:
        val = json.loads(val_path.read_text(encoding="utf-8"))
    except Exception as e:
        return None, {"reason": f"{val_path.name} ilegible (JSON corrupto): {e}", "notes": notes}

    # El DCF no aplica a financieras/REITs/aseguradoras (se valoran por P/Book, P/FFO,
    # embedded value...). Se marcan como no verificables en vez de forzar una
    # comparacion absurda. Mismo criterio que el futuro router de metodos.
    sector = (val.get("sector") or "").lower()
    industry = (val.get("industry") or "").lower()
    if any(x in sector for x in ("financial", "bank", "insurance")) \
       or any(x in industry for x in ("reit", "real estate", "insurance", "bank")):
        return None, {"reason": (
            f"sector financiero/inmobiliario (sector='{val.get('sector')}', "
            f"industry='{val.get('industry')}'): el DCF estándar no aplica. Los fair "
            f"values NO quedan verificados por el motor — valora por P/Book, SoP o "
            f"embedded value y deja el método y su aritmética explícitos en la tesis"),
            "notes": notes}

    lf = val.get("latest_financials", {})
    revenue = lf.get("revenue")
    shares = val.get("shares_outstanding") or 0
    net_debt = (lf.get("total_debt") or 0) - (lf.get("cash") or 0)
    if not revenue or not shares:
        return None, {"reason": (
            f"faltan revenue o shares_outstanding en {val_path.name} "
            f"(revenue={revenue}, shares={shares})"), "notes": notes}

    # Overrides que la tesis pudo declarar (esquema canonico unico — ver _normalize_meta).
    # Opus decide; la verificacion los respeta para no marcar como "error de calculo"
    # una decision deliberada (revenue base FY-forward, share count del 10-K, deuda
    # pre-IFRS16). Un override explicito manda sobre las heuristicas de abajo.
    norm = _normalize_meta(meta)

    # El ratio market_cap / (precio * acciones) delata inconsistencias de escala en
    # los datos de Yahoo (debe ser ~1.0 si todo es coherente):
    price = val.get("current_price") or 0
    mcap = val.get("market_cap") or 0
    ratio = mcap / (price * shares) if (mcap and price and shares) else 1.0

    # (a) Peniques (UK): precio en GBp pero fundamentales en GBP -> ratio ~0.01.
    #     El fair value se calcula en libras y se pasa a peniques (x100) para comparar
    #     con el guardado. Misma correccion que hacia el Excel, detectada por el ratio
    #     porque el valuation.json normaliza la moneda a "GBP" y pierde la marca.
    pence_factor = 1
    if ratio < 0.02:
        pence_factor = 100
        notes.append(f"precio en peniques GBp detectado (ratio mcap/(precio×acciones) = "
                     f"{ratio:.4f}): fair values calculados en GBP y convertidos ×100")

    # (b) Acciones de estructura dual: si el market cap es muy superior a precio*acciones,
    #     shares_outstanding es solo de una clase (p. ej. PUIG). Las acciones reales son
    #     market_cap / precio (la verdad la marca la capitalizacion).
    #     Desde el fix en la fuente (financial_data._reconcile_shares) los valuation.json
    #     nuevos ya nacen corregidos (ratio ~1.0, esta rama es no-op). Se mantiene como
    #     red defensiva para los JSON antiguos en disco, escritos antes de ese cambio.
    #     Un shares_override explicito de la tesis manda sobre esta heuristica.
    if norm["shares_override"] is not None:
        shares = norm["shares_override"]
        notes.append(f"override de acciones de la tesis: {shares:,.0f}")
    elif ratio > 1.5 and price:
        shares = mcap / price
        notes.append(f"acciones duales detectadas (ratio {ratio:.2f}): usando "
                     f"market_cap/precio = {shares:,.0f} acciones")
    elif pence_factor == 1 and not 0.8 <= ratio <= 1.2:
        # Zona gris: ni peniques ni dual-class, pero la escala no cuadra. Ninguna
        # heuristica corrige -> el fair value hereda el error. Avisar, no adivinar.
        notes.append(f"ratio mcap/(precio×acciones) = {ratio:.2f} fuera de lo sano (~1.0) "
                     f"y sin corrección aplicable: revisa market_cap, precio o acciones "
                     f"del valuation.json antes de fiarte de esta verificación")

    # (c) Deuda neta: la tesis puede declarar un override (p. ej. pre-IFRS16 en retailers
    #     con muchos arrendamientos, donde el total_debt de Yahoo esta inflado por el
    #     leasing). Se respeta ese criterio.
    if norm["net_debt_override_m"] is not None:
        net_debt = float(norm["net_debt_override_m"]) * 1e6
        notes.append(f"override de deuda neta de la tesis: {norm['net_debt_override_m']:,.0f}M")

    # (d) Revenue base: la tesis puede fijar el revenue del año 0 (p. ej. un trading
    #     update FY-forward posterior al ultimo FY reportado en el valuation.json).
    #     Viene en millones. Cierra divergencias como WOSG_L (-10% por base distinta).
    if norm["revenue_base_m"] is not None:
        revenue = float(norm["revenue_base_m"]) * 1e6
        notes.append(f"override de revenue base de la tesis: {norm['revenue_base_m']:,.0f}M")

    return ({"revenue": revenue, "shares": shares, "net_debt": net_debt,
             "pence_factor": pence_factor, "price": price},
            {"reason": None, "notes": notes})


def _engine_fair_values(scenarios: dict, output_dir, folder: str, meta: dict | None = None):
    """Recalcula los fair values con el motor (DCF determinista) a partir de los
    supuestos de cada escenario + los datos de la empresa. Es la comprobación de que
    los numeros de la tesis cuadran con sus propios supuestos: Opus decide los
    supuestos, el motor verifica la aritmetica.

    Devuelve (fvs, info): fvs = {'bear':.., 'base':.., 'bull':..} o None cuando no
    aplica; info = {"reason", "notes"} SIEMPRE explica el porqué (nunca silencioso)."""
    if not scenarios:
        return None, {"reason": "thesis_data.json sin bloque 'scenarios' (si la tesis usa "
                                "un método no-DCF, decláralo y documenta su aritmética en "
                                "la propia tesis)", "notes": []}
    inputs, info = _dcf_inputs(output_dir, folder, meta)
    if inputs is None:
        return None, info

    try:
        from tools.valuation_engine import DCFAssumptions, run_dcf
    except Exception as e:
        info["reason"] = f"no se pudo importar el motor de valoración: {e}"
        return None, info

    out = {}
    for name in ("bear", "base", "bull"):
        sc = scenarios.get(name)
        if not isinstance(sc, dict):
            info["reason"] = f"falta el escenario '{name}' en thesis_data.json"
            return None, info
        try:
            growth = [sc[f"revenue_growth_y{i}"] for i in range(1, 6)]
            assumptions = DCFAssumptions(
                revenue_base=inputs["revenue"], revenue_growth=growth,
                gross_margin=sc["gross_margin"], sga_pct=sc["sga_pct"], rd_pct=sc["rd_pct"],
                da_pct=sc["da_pct"], capex_pct=sc["capex_pct"], tax_rate=sc["tax_rate"],
                wacc=sc["wacc"], terminal_multiple=sc["terminal_multiple"],
            )
            out[name] = (run_dcf(assumptions, inputs["net_debt"], inputs["shares"], name)
                         .fair_value_per_share * inputs["pence_factor"])
        except KeyError as e:
            info["reason"] = (f"escenario '{name}': falta el campo {e} "
                              f"(¿método no-DCF? decláralo en la tesis)")
            return None, info
        except (ValueError, ZeroDivisionError) as e:
            info["reason"] = f"escenario '{name}': {e}"
            return None, info
    return out, info


def _compare_engine(saved: dict, engine_fvs: dict | None, fv_adj: dict | None) -> dict | None:
    """Compara los fair values de la tesis contra el motor, aplicando el ajuste
    deliberado declarado por la tesis (motor*(1+pct)) si lo hay. Puro: no imprime.

    'saved' = {bear, base, bull} de la tesis. Devuelve None si no hay nada que
    comparar; si no, {rows, max_diff, adj_pct, explained}, donde rows lista
    {name, saved, engine, target, diff_pct} (target = motor ajustado) y 'explained'
    indica si la divergencia residual (tesis vs motor ajustado) entra en tolerancia."""
    if not engine_fvs:
        return None
    adj_pct = fv_adj["pct"] if fv_adj else 0.0
    rows = []
    max_diff = 0.0
    for name in ("bear", "base", "bull"):
        s = saved.get(name)
        m = engine_fvs.get(name)
        if not s or m is None:
            continue
        target = m * (1 + adj_pct)
        diff = (target - s) / s * 100
        max_diff = max(max_diff, abs(diff))
        rows.append({"name": name, "saved": s, "engine": m, "target": target, "diff_pct": diff})
    if not rows:
        return None
    return {"rows": rows, "max_diff": max_diff, "adj_pct": adj_pct, "explained": max_diff <= 3}


def _scenario_assumptions(sc: dict, revenue: float, **overrides):
    """Construye DCFAssumptions desde un escenario de thesis_data, con overrides
    puntuales (wacc, terminal_multiple, revenue_growth...). Lanza KeyError/ValueError
    si el escenario está incompleto o fuera de rango — el llamador decide qué hacer."""
    from tools.valuation_engine import DCFAssumptions
    params = dict(
        revenue_base=revenue,
        revenue_growth=[sc[f"revenue_growth_y{i}"] for i in range(1, 6)],
        gross_margin=sc["gross_margin"], sga_pct=sc["sga_pct"], rd_pct=sc["rd_pct"],
        da_pct=sc["da_pct"], capex_pct=sc["capex_pct"], tax_rate=sc["tax_rate"],
        wacc=sc["wacc"], terminal_multiple=sc["terminal_multiple"],
    )
    params.update(overrides)
    return DCFAssumptions(**params)


def _sensitivity_grid(base_sc: dict, inputs: dict) -> dict | None:
    """Tabla de sensibilidad del fair value (escenario base): WACC ±1pt × múltiplo
    terminal ±2x. PURO (no imprime). El motor es determinista, así que esta tabla sale
    gratis y evita que la de la tesis se calcule a mano (donde se cuela un error).

    Devuelve {"waccs": [..3], "multiples": [..3], "grid": [[fv|None]]} o None si el
    escenario base no es apto para el DCF (campos ausentes o fuera de rango)."""
    from tools.valuation_engine import run_dcf
    try:
        w0 = float(base_sc["wacc"])
        m0 = float(base_sc["terminal_multiple"])
    except (KeyError, TypeError):
        return None
    waccs = [w0 - 0.01, w0, w0 + 0.01]
    multiples = [m0 - 2, m0, m0 + 2]
    grid = []
    any_ok = False
    for w in waccs:
        row = []
        for m in multiples:
            try:
                a = _scenario_assumptions(base_sc, inputs["revenue"],
                                          wacc=w, terminal_multiple=m)
                fv = (run_dcf(a, inputs["net_debt"], inputs["shares"], "sens")
                      .fair_value_per_share * inputs["pence_factor"])
                row.append(fv)
                any_ok = True
            except (KeyError, ValueError, ZeroDivisionError):
                row.append(None)  # celda fuera de rango (p. ej. múltiplo <= 0)
        grid.append(row)
    return {"waccs": waccs, "multiples": multiples, "grid": grid} if any_ok else None


def _implied_growth(base_sc: dict, inputs: dict) -> float | None:
    """Reverse DCF: crecimiento anual UNIFORME que justifica el precio actual con el
    resto de supuestos del escenario base (márgenes, WACC, múltiplo). PURO.

    Es el chequeo anti-optimismo más barato: si el precio ya descuenta más crecimiento
    del que asume tu base, el 'margen de seguridad' es una opinión, no un margen.
    Devuelve g (fracción) o None si el precio no se alcanza en g ∈ [-0.5, 1.0] o el
    escenario no es apto (p. ej. método no-DCF)."""
    from tools.valuation_engine import run_dcf
    price = inputs.get("price") or 0
    if price <= 0:
        return None
    target = price / inputs["pence_factor"]   # el motor calcula en GBP; precio en GBp

    def fv(g: float) -> float:
        a = _scenario_assumptions(base_sc, inputs["revenue"], revenue_growth=[g] * 5)
        return run_dcf(a, inputs["net_debt"], inputs["shares"], "reverse").fair_value_per_share

    try:
        lo, hi = -0.5, 1.0
        f_lo, f_hi = fv(lo), fv(hi)
    except (KeyError, ValueError, ZeroDivisionError):
        return None
    if not (min(f_lo, f_hi) <= target <= max(f_lo, f_hi)):
        return None  # el precio implica crecimiento fuera de [-50%, +100%]: revisar método
    creciente = f_hi >= f_lo
    for _ in range(60):  # bisección: 60 iteraciones ≈ precisión 1e-18, de sobra
        mid = (lo + hi) / 2
        try:
            f_mid = fv(mid)
        except (ValueError, ZeroDivisionError):
            return None
        if (f_mid < target) == creciente:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def finalize_thesis(ticker: str, data: dict, force: bool = False):
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

    err = validate_fair_values(bear, base, bull)
    if err:
        print(f"Error: {err}")
        sys.exit(1)

    # Review gate: no publicar una tesis con checks críticos en rojo (salvo --force).
    if not force:
        _run_review_gate(ticker, output_dir, folder)

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

    # --- 1b. Verificacion con el motor de valoracion (DCF determinista) ---
    # Opus decide los supuestos; el motor comprueba que los fair values tecleados
    # cuadran con esos supuestos. Una desviacion DELIBERADA se declara como
    # _meta.fv_adjustment (la verificacion la respeta comparando contra motor*(1+pct)).
    # Solo informa, nunca bloquea: el motor manda sobre la aritmetica, no sobre la tesis.
    engine_fvs, engine_info = _engine_fair_values(scenarios, output_dir, folder, data.get("_meta"))
    fv_adj = _normalize_meta(data.get("_meta")).get("fv_adjustment")
    cmp = _compare_engine({"bear": bear, "base": base, "bull": bull}, engine_fvs, fv_adj)
    if cmp:
        print(f"\n  === Verificacion del motor (DCF) ===")
        if fv_adj:
            print(f"    Ajuste declarado: {fv_adj['pct']:+.0%} — {fv_adj['reason']}")
            print(f"    {'Escenario':<9} {'Tesis':>10} {'Motor':>10} {'Motor aj.':>10} {'Dif':>8}")
            for r in cmp["rows"]:
                flag = "OK" if abs(r["diff_pct"]) <= 3 else "REVISAR"
                print(f"    {r['name'].capitalize():<9} {r['saved']:>10.2f} {r['engine']:>10.2f} "
                      f"{r['target']:>10.2f} {r['diff_pct']:>+7.1f}%  {flag}")
        else:
            print(f"    {'Escenario':<9} {'Tesis':>10} {'Motor':>10} {'Dif':>8}")
            for r in cmp["rows"]:
                flag = "OK" if abs(r["diff_pct"]) <= 3 else "REVISAR"
                print(f"    {r['name'].capitalize():<9} {r['saved']:>10.2f} {r['engine']:>10.2f} "
                      f"{r['diff_pct']:>+7.1f}%  {flag}")
        for n in engine_info["notes"]:
            print(f"    [aviso] {n}")
        if cmp["explained"]:
            tail = " + el ajuste declarado" if fv_adj else ""
            print(f"  [OK] Los fair values cuadran con los supuestos{tail} (<=3%).")
        elif fv_adj:
            print(f"  [!] Divergencia de hasta {cmp['max_diff']:.0f}% INCLUSO tras el ajuste "
                  f"declarado ({fv_adj['pct']:+.0%}). Revisa el calculo, el pct o los supuestos.")
        else:
            print(f"  [!] Divergencia de hasta {cmp['max_diff']:.0f}% entre la tesis y sus "
                  f"supuestos, sin ajuste declarado.")
            print(f"      Si es deliberada (opcionalidad, SoP parcial, prima/descuento...),")
            print(f"      declarala: _meta.fv_adjustment = {{\"pct\": <±0.NN>, \"reason\": \"...\"}}.")
            print(f"      Si no, el numero tiene un error de calculo o los datos cambiaron: revisar.")
    else:
        # NUNCA silencioso: distinguir el caso legítimo (financiera, método no-DCF
        # declarado) del bug (JSON roto, campo que falta, input fuera de rango).
        print(f"\n  [Motor] Fair values NO verificados: {engine_info['reason']}")
        for n in engine_info["notes"]:
            print(f"    [aviso] {n}")

    # --- 1c. Sensibilidad y reverse-DCF (informativos, salen gratis del motor) ---
    if engine_fvs:
        inputs, _ = _dcf_inputs(output_dir, folder, data.get("_meta"))
        base_sc = scenarios.get("base") or {}
        sens = _sensitivity_grid(base_sc, inputs) if inputs else None
        if sens:
            print(f"\n  === Sensibilidad (motor, escenario base) ===")
            header = "    {:<12}".format("")
            header += "".join(f"{'TV ' + format(m, '.0f') + 'x':>12}" for m in sens["multiples"])
            print(header)
            for w, row in zip(sens["waccs"], sens["grid"]):
                cells = "".join(f"{fv:>12,.2f}" if fv is not None else f"{'—':>12}" for fv in row)
                print(f"    WACC {w:>5.1%} {cells}")
        if inputs and inputs.get("price"):
            g = _implied_growth(base_sc, inputs)
            growths = [base_sc.get(f"revenue_growth_y{i}") for i in range(1, 6)]
            avg_base = (sum(growths) / 5) if all(isinstance(x, (int, float)) for x in growths) else None
            if g is not None:
                print(f"\n  === Reverse DCF (motor) ===")
                line = (f"    El precio actual ({inputs['price']:,.2f}) implica ~{g:+.1%} de "
                        f"crecimiento anual (5a) con los márgenes/WACC/múltiplo del base")
                if avg_base is not None:
                    line += f"; tu base asume {avg_base:+.1%} medio."
                    print(line)
                    if avg_base - g > 0.02:
                        print(f"    [!] Tu base asume {(avg_base - g) * 100:.1f} puntos MÁS de "
                              f"crecimiento del que el precio ya descuenta: el margen de "
                              f"seguridad depende de ese exceso. Justifícalo en la tesis.")
                else:
                    print(line + ".")

    # --- 2. Resumen de escenarios ---
    # Antes aquí se regeneraba el modelo Excel (otra vez get_company_data + un DCF por
    # fórmulas). Se obvió del pipeline: el motor hace la aritmética, la verificación la
    # confirma y nadie consumía el .xlsx. Como efecto colateral, finalize YA NO llama a
    # la red. excel_generator se conserva inactivo por si se reactiva (ver REDISENO).
    if scenarios and all(k in scenarios for k in ("bear", "base", "bull")):
        print(f"\n  Escenarios (supuestos de la tesis):")
        for name in ["bear", "base", "bull"]:
            sc = scenarios[name]
            if all(k in sc for k in ("wacc", "terminal_multiple", "revenue_growth_y1", "gross_margin")):
                print(f"    {name.capitalize():5s}: WACC={sc['wacc']:.1%}, "
                      f"TV={sc['terminal_multiple']:.0f}x, "
                      f"Growth Y1={sc['revenue_growth_y1']:.1%}, "
                      f"GM={sc['gross_margin']:.1%}")


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
    parser.add_argument("--force", action="store_true",
                        help="Finalizar aunque el review gate falle (saltar checks críticos)")
    args = parser.parse_args()

    if args.clean_all:
        clean_all_history()
    elif args.ticker and args.data_file:
        with open(args.data_file, encoding="utf-8") as f:
            data = json.load(f)
        finalize_thesis(args.ticker, data, force=args.force)
    else:
        parser.print_help()
