"""
main.py — CLI del sistema de inversión.

Python recoge datos. Claude Code (Opus) interpreta y valora vía skills.

Uso:
    python main.py --analyst AAPL             # Recoger datos (Excel + JSON + SEC)
    python main.py --analyst AAPL MSFT GOOGL  # Múltiples tickers
    python main.py --compare AAPL MSFT        # Datos para comparar dos empresas
    python main.py --screener graham_default  # Buscar ideas value
    python main.py --history TICKER           # Historial de valoraciones
    python main.py --portfolio status         # Estado de cartera
    python main.py --fresh --analyst TICKER   # Forzar refresh de caché
"""
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.analyst import run_analyst, load_history
from agents.screener import run_screener
from agents.portfolio_tracker import run_portfolio_tracker
from tools.quality_gates import validate_valuation, print_quality_report


def main():
    parser = argparse.ArgumentParser(
        description="Sistema de inversión — Python recoge datos, Claude Code interpreta",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py --analyst AAPL MSFT GOOGL
  python main.py --compare AAPL MSFT
  python main.py --screener graham_default
  python main.py --history DE
  python main.py --portfolio status
  python main.py --fresh --analyst DE
        """
    )

    parser.add_argument("--analyst", nargs="+", metavar="TICKER",
                        help="Recoger datos: Excel + JSON + SEC filings")
    parser.add_argument("--compare", nargs=2, metavar="TICKER",
                        help="Recoger datos de dos empresas para comparar")
    parser.add_argument("--screener", metavar="FILTER", nargs="?", const="graham_default",
                        help="Buscar ideas value (filtros cuantitativos)")
    parser.add_argument("--history", metavar="TICKER",
                        help="Historial de valoraciones de un ticker")
    parser.add_argument("--portfolio", metavar="ACTION", default=None,
                        help="Gestiona cartera: status|update_prices")
    parser.add_argument("--fresh", action="store_true",
                        help="Forzar descarga de datos frescos (ignorar caché)")

    args = parser.parse_args()

    # Forzar datos frescos
    if args.fresh:
        from config import settings as _settings
        _settings.FORCE_FRESH = True
        print("[fresh] Ignorando caché, descarga forzada\n")

    # --- Comandos ---

    if args.analyst:
        for ticker in args.analyst:
            t = ticker.upper()
            print(f"\n=== Datos: {t} ===")
            result = run_analyst(t)
            print_quality_report(validate_valuation(result))
            _print_data_summary(result)

    elif args.compare:
        ticker1, ticker2 = args.compare[0].upper(), args.compare[1].upper()
        print(f"\n=== Comparación: {ticker1} vs {ticker2} ===")
        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(run_analyst, ticker1)
            f2 = executor.submit(run_analyst, ticker2)
            r1, r2 = f1.result(), f2.result()
        print_quality_report(validate_valuation(r1))
        print_quality_report(validate_valuation(r2))
        print(f"\n  Datos generados para ambas empresas.")
        print(f"  JSON 1: data/valuations/{ticker1.replace('.', '_')}/")
        print(f"  JSON 2: data/valuations/{ticker2.replace('.', '_')}/")
        print(f"  Usa Claude Code para interpretar y comparar.")

    elif args.history:
        ticker = args.history.upper()
        history = load_history(ticker)
        if not history:
            print(f"\nNo hay historial para {ticker}.")
        else:
            print(f"\n=== Historial de {ticker} ({len(history)} entrada(s)) ===\n")
            print(f"  {'Fecha':12s} {'Precio':>10s} {'Bear':>10s} "
                  f"{'Base':>10s} {'Bull':>10s} {'EV/EBITDA':>10s}")
            print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
            for h in history:
                cur = h.get("currency", "$")
                price = h.get("current_price", 0)
                bear = h.get("fair_value_bear", 0)
                base = h.get("fair_value_base", 0)
                bull = h.get("fair_value_bull", 0)
                ev_ebitda = h.get("ev_ebitda", 0) or 0
                bear_str = f"{cur}{bear:>9,.2f}" if bear else "      —"
                base_str = f"{cur}{base:>9,.2f}" if base else "      —"
                bull_str = f"{cur}{bull:>9,.2f}" if bull else "      —"
                ev_str = f"{ev_ebitda:>9.1f}x" if ev_ebitda else "      —"
                print(f"  {h['date']:12s} {cur}{price:>9,.2f} {bear_str} "
                      f"{base_str} {bull_str} {ev_str}")

    elif args.portfolio is not None:
        print(f"\n=== Portfolio: {args.portfolio} ===")
        print(run_portfolio_tracker(action=args.portfolio))

    elif args.screener is not None:
        print(f"\n=== Screener: {args.screener} ===")
        result = run_screener(filter_name=args.screener)
        print(f"  Candidatos encontrados: {result.get('total_candidates_found', 0)}")
        for c in result.get("top_candidates", []):
            ticker = c.get("ticker", c.get("symbol", "?"))
            name = c.get("name", c.get("shortName", ""))
            print(f"  {ticker:8s} {name}")

    else:
        parser.print_help()


def _print_data_summary(v):
    """Muestra resumen de los datos recogidos."""
    if v.get("error"):
        return
    ticker = v.get("ticker", "?")
    currency = v.get("currency", "$")
    price = v.get("current_price", 0)
    print(f"\n  {ticker} | {v.get('company', '')}")
    print(f"  Precio: {currency}{price:,.2f} | Sector: {v.get('sector', 'N/A')}")
    metrics = v.get("reference_metrics", {})
    if metrics:
        m = metrics.get("avg_margins", {})
        print(f"  Márgenes avg: GM={m.get('gross_margin', 0):.1%}, "
              f"SGA={m.get('sga_pct', 0):.1%}")
        if metrics.get("ev_ebitda"):
            print(f"  EV/EBITDA: {metrics['ev_ebitda']:.1f}x")
    if v.get("files", {}).get("excel"):
        print(f"  Excel: {v['files']['excel']}")
    print(f"  → Usa Claude Code para interpretar datos y escribir tesis")


if __name__ == "__main__":
    main()
