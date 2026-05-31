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


def _engine_fair_values(scenarios: dict, output_dir, folder: str, meta: dict | None = None):
    """Recalcula los fair values con el motor (DCF determinista) a partir de los
    supuestos de cada escenario + los datos de la empresa. Es la comprobación de que
    los numeros de la tesis cuadran con sus propios supuestos: Opus decide los
    supuestos, el motor verifica la aritmetica.

    Devuelve {'bear':.., 'base':.., 'bull':..} o None cuando no aplica (faltan
    campos del escenario -> metodo no-DCF, o faltan datos de la empresa)."""
    val_path = output_dir / f"{folder}_valuation.json"
    if not (scenarios and val_path.exists()):
        return None
    try:
        val = json.loads(val_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    # El DCF no aplica a financieras/REITs/aseguradoras (se valoran por P/Book, P/FFO,
    # embedded value...). Se marcan como no verificables en vez de forzar una
    # comparacion absurda. Mismo criterio que el futuro router de metodos.
    sector = (val.get("sector") or "").lower()
    industry = (val.get("industry") or "").lower()
    if any(x in sector for x in ("financial", "bank", "insurance")) \
       or any(x in industry for x in ("reit", "real estate", "insurance", "bank")):
        return None

    lf = val.get("latest_financials", {})
    revenue = lf.get("revenue")
    shares = val.get("shares_outstanding") or 0
    net_debt = (lf.get("total_debt") or 0) - (lf.get("cash") or 0)
    if not revenue or not shares:
        return None

    # El ratio market_cap / (precio * acciones) delata inconsistencias de escala en
    # los datos de Yahoo (debe ser ~1.0 si todo es coherente):
    price = val.get("current_price") or 0
    mcap = val.get("market_cap") or 0
    ratio = mcap / (price * shares) if (mcap and price and shares) else 1.0

    # (a) Peniques (UK): precio en GBp pero fundamentales en GBP -> ratio ~0.01.
    #     El fair value se calcula en libras y se pasa a peniques (x100) para comparar
    #     con el guardado. Misma correccion que el pence_factor del Excel, detectada por
    #     el ratio porque el valuation.json normaliza la moneda a "GBP" y pierde la marca.
    pence_factor = 100 if ratio < 0.02 else 1

    # (b) Acciones de estructura dual: si el market cap es muy superior a precio*acciones,
    #     shares_outstanding es solo de una clase (p. ej. PUIG). Las acciones reales son
    #     market_cap / precio (la verdad la marca la capitalizacion).
    if ratio > 1.5 and price:
        shares = mcap / price

    # (c) Deuda neta: la tesis puede declarar un override (p. ej. pre-IFRS16 en retailers
    #     con muchos arrendamientos, donde el total_debt de Yahoo esta inflado por el
    #     leasing). Se respeta ese criterio, igual que hace el Excel.
    if meta and meta.get("net_debt_override_m") is not None:
        net_debt = float(meta["net_debt_override_m"]) * 1e6

    try:
        from tools.valuation_engine import DCFAssumptions, run_dcf
    except Exception:
        return None

    out = {}
    for name in ("bear", "base", "bull"):
        sc = scenarios.get(name)
        if not isinstance(sc, dict):
            return None
        try:
            growth = [sc[f"revenue_growth_y{i}"] for i in range(1, 6)]
            assumptions = DCFAssumptions(
                revenue_base=revenue, revenue_growth=growth,
                gross_margin=sc["gross_margin"], sga_pct=sc["sga_pct"], rd_pct=sc["rd_pct"],
                da_pct=sc["da_pct"], capex_pct=sc["capex_pct"], tax_rate=sc["tax_rate"],
                wacc=sc["wacc"], terminal_multiple=sc["terminal_multiple"],
            )
            out[name] = run_dcf(assumptions, net_debt, shares, name).fair_value_per_share * pence_factor
        except (KeyError, ValueError, ZeroDivisionError):
            return None  # escenario incompleto o no apto para este DCF
    return out


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
    # cuadran con esos supuestos. Por ahora solo informa (no sobreescribe ni bloquea).
    engine_fvs = _engine_fair_values(scenarios, output_dir, folder, data.get("_meta"))
    if engine_fvs:
        print(f"\n  === Verificacion del motor (DCF) ===")
        print(f"    {'Escenario':<9} {'Tesis':>10} {'Motor':>10} {'Dif':>8}")
        max_diff = 0.0
        for name, saved in (("bear", bear), ("base", base), ("bull", bull)):
            m = engine_fvs.get(name)
            if m is None or not saved:
                continue
            diff = (m - saved) / saved * 100
            max_diff = max(max_diff, abs(diff))
            flag = "OK" if abs(diff) <= 3 else "REVISAR"
            print(f"    {name.capitalize():<9} {saved:>10.2f} {m:>10.2f} {diff:>+7.1f}%  {flag}")
        if max_diff <= 3:
            print(f"  [OK] Los fair values cuadran con los supuestos (motor coincide <=3%).")
        else:
            print(f"  [!] Divergencia de hasta {max_diff:.0f}% entre la tesis y sus supuestos.")
            print(f"      O el numero de la tesis tiene un error de calculo, o los datos")
            print(f"      del valuation.json cambiaron desde que se escribio. Conviene revisar.")
    else:
        print(f"\n  [Motor] Fair values no verificados (metodo no-DCF o datos insuficientes).")

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

            # Net debt decidido en la tesis (p. ej. pre-IFRS16 en retailers). Si el
            # thesis_data trae _meta.net_debt_override_m, el Excel lo usa en vez del
            # de Yahoo, que para acciones con muchos arrendamientos está inflado.
            meta = data.get("_meta", {}) if isinstance(data, dict) else {}
            nd_override = meta.get("net_debt_override_m")
            if nd_override is not None:
                metrics["_net_debt_override_m"] = nd_override
            sh_override = meta.get("shares_override")
            if sh_override is not None:
                metrics["_shares_override"] = sh_override

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
