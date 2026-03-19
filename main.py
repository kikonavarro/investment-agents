"""
main.py — CLI del sistema multi-agente de inversion.

Uso:
    python main.py                        # Modo interactivo
    python main.py "Analiza AAPL"         # Modo directo
    python main.py --analyst AAPL         # Valoracion completa (Excel + JSON)
    python main.py --thesis AAPL          # Valoracion + tesis
    python main.py --portfolio status     # Estado de cartera
    python main.py --screener             # Buscar ideas value
"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import orchestrate
from agents.analyst import run_analyst, load_valuation, quick_summary
from agents.news_fetcher import run_news_fetcher
from agents.thesis_writer import run_thesis_writer
from agents.social_media import run_social_media
from agents.portfolio_tracker import run_portfolio_tracker
from agents.content_writer import run_content_writer
from agents.screener import run_screener
from tools.document_generator import save_analysis_json, save_screener_report

AGENT_MAP = {
    "analyst": run_analyst,
    "news_fetcher": run_news_fetcher,
    "thesis_writer": run_thesis_writer,
    "social_media": run_social_media,
    "portfolio_tracker": run_portfolio_tracker,
    "content_writer": run_content_writer,
    "screener": run_screener,
}


def run_pipeline(user_input: str) -> dict:
    """Ejecuta el pipeline: orquestador -> agentes -> resultados."""
    print(f"\nInstruccion: {user_input}")
    steps = orchestrate(user_input)
    print(f"Plan: {json.dumps(steps, ensure_ascii=False)}\n")

    context = {"_steps": steps}
    for step in steps:
        agent_name = step["agent"]
        agent_input = step["input"]
        if agent_name not in AGENT_MAP:
            print(f"[!] Agente desconocido: {agent_name}")
            continue

        print(f"--- {agent_name.upper()} ---")
        resolved_input = _resolve_input(agent_input, agent_name, context)
        result = _call_agent(agent_name, resolved_input)
        context[f"{agent_name}_output"] = result
        _print_result(agent_name, result)

    return context


def _resolve_input(agent_input, agent_name, context):
    s = str(agent_input).lower()
    if "from_analyst" in s or s == "from_analyst":
        return context.get("analyst_output", {})
    if agent_input == "from_screener_top3":
        top5 = context.get("screener_output", {}).get("top_5", [])
        return [t["ticker"] for t in top5[:3]]
    if "from_news" in s or s == "from_news":
        return context.get("news_fetcher_output", {})
    return agent_input


def _call_agent(agent_name, agent_input):
    fn = AGENT_MAP[agent_name]
    if agent_name == "analyst":
        if isinstance(agent_input, list):
            return [fn(t) for t in agent_input]
        return fn(str(agent_input))
    elif agent_name == "thesis_writer":
        # Auto-ejecutar analyst si no existe valoración previa
        if isinstance(agent_input, str):
            ticker = agent_input.upper()
            if load_valuation(ticker) is None:
                print(f"  No existe valoracion para {ticker}. Ejecutando analyst primero...")
                run_analyst(ticker)
        return fn(agent_input)
    elif agent_name == "news_fetcher":
        return fn(str(agent_input))
    elif agent_name == "social_media":
        content = agent_input if isinstance(agent_input, dict) else {"input": agent_input}
        content_type = "news" if "news_items" in content else "analysis"
        return fn(content, content_type=content_type)
    elif agent_name == "portfolio_tracker":
        action = agent_input if isinstance(agent_input, str) else "status"
        return fn(action=action)
    elif agent_name == "content_writer":
        if isinstance(agent_input, dict):
            if "news_formatted" in agent_input:
                return fn(topic=f"Novedades de {agent_input['ticker']}", supporting_data=agent_input)
            elif "ticker" in agent_input:
                # Viene del analyst — usar nombre de empresa como topic
                company = agent_input.get("company") or agent_input["ticker"]
                return fn(topic=f"Catalizadores de inversión en {company} ({agent_input['ticker']})", supporting_data=agent_input)
        return fn(topic=str(agent_input))
    elif agent_name == "screener":
        return fn(filter_name=agent_input if isinstance(agent_input, str) else "graham_default")
    return fn(agent_input)


def _print_result(agent_name, result):
    if agent_name == "analyst":
        if isinstance(result, list):
            for r in result:
                _print_quick_summary(r)
        else:
            _print_quick_summary(result)
    elif agent_name == "thesis_writer":
        print(result)
    elif agent_name == "social_media":
        for i, tweet in enumerate(result, 1):
            print(f"\n[{i}] {tweet}")
    elif agent_name == "news_fetcher":
        print(result.get("news_formatted", "Sin noticias"))
    elif agent_name == "screener":
        if result.get("_data_only"):
            print(f"  Candidatos encontrados: {result.get('total_candidates_found', 0)}")
            for c in result.get("top_candidates", []):
                ticker = c.get("ticker", c.get("symbol", "?"))
                name = c.get("name", c.get("shortName", ""))
                print(f"  {ticker:8s} {name}")
        else:
            for item in result.get("top_5", []):
                print(f"  #{item['rank']} {item['ticker']:8s} -- {item['reason']}")
    elif isinstance(result, str):
        print(result)
    elif isinstance(result, dict):
        print(json.dumps(result, indent=2, ensure_ascii=False))


def _print_quick_summary(v):
    """Genera y muestra el resumen rápido con 3 escenarios + conclusión."""
    ticker = v.get("ticker", "?")
    print(f"\n  Generando resumen de {ticker}...")
    try:
        summary = quick_summary(ticker)
        print(f"\n{summary}")
    except Exception as e:
        print(f"  [!] Error generando resumen: {e}")
        _print_valuation_fallback(v)
    if v.get("files", {}).get("excel"):
        print(f"\n  Excel: {v['files']['excel']}")


def _print_valuation_fallback(v):
    """Fallback si el resumen rápido falla."""
    ticker = v.get("ticker", "?")
    price = v.get("current_price", 0)
    currency = v.get("currency", "$")
    print(f"\n  {ticker} | {v.get('company', '')}")
    print(f"  Precio: {currency}{price:,.2f} | Sector: {v.get('sector', 'N/A')}")
    for name in ("bear", "base", "bull"):
        sc = v.get("scenarios", {}).get(name, {})
        if sc:
            print(f"  {name.capitalize():5s}: Growth Y1={sc.get('revenue_growth_y1', 0):.1%}, "
                  f"WACC={sc.get('wacc', 0):.1%}, TV={sc.get('terminal_multiple', 0):.0f}x")


def main():
    parser = argparse.ArgumentParser(
        description="Sistema multi-agente de inversion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py "Analiza AAPL"
  python main.py "Valora AAPL y escribe la tesis"
  python main.py --analyst AAPL MSFT GOOGL
  python main.py --thesis AAPL
  python main.py --portfolio status
  python main.py --screener graham_default
        """
    )

    parser.add_argument("query", nargs="?", help="Instruccion en lenguaje natural")
    parser.add_argument("--analyst", nargs="+", metavar="TICKER",
                        help="Valoracion completa: Excel + JSON + SEC filings")
    parser.add_argument("--thesis", metavar="TICKER",
                        help="Escribe tesis (ejecuta valoracion si no existe)")
    parser.add_argument("--portfolio", metavar="ACTION", default=None,
                        help="Gestiona cartera: status|update_prices|...")
    parser.add_argument("--screener", metavar="FILTER", nargs="?", const="graham_default",
                        help="Busca ideas value")
    parser.add_argument("--tweets", metavar="TICKER", help="Genera tweets")
    parser.add_argument("--article", metavar="TOPIC", help="Escribe articulo Substack")
    parser.add_argument("--data-only", action="store_true",
                        help="Solo ejecuta Python (datos/Excel/filtros), sin llamadas API de Claude")

    args = parser.parse_args()

    # Activar modo data-only si se pasa el flag
    if args.data_only:
        from config import settings
        settings.DATA_ONLY_MODE = True
        print("[modo data-only] Sin llamadas API de Claude\n")

    if args.analyst:
        for ticker in args.analyst:
            t = ticker.upper()
            print(f"\n=== Valoracion: {t} ===")
            result = run_analyst(t)
            _print_quick_summary(result)

    elif args.thesis:
        ticker = args.thesis.upper()
        existing = load_valuation(ticker)
        if existing is None:
            print(f"\nNo existe valoracion previa para {ticker}. Ejecutando primero...")
            run_analyst(ticker)
        print(f"\n=== Redactando tesis: {ticker} ===")
        thesis = run_thesis_writer(ticker)
        print(thesis)

    elif args.portfolio is not None:
        print(f"\n=== Portfolio: {args.portfolio} ===")
        print(run_portfolio_tracker(action=args.portfolio))

    elif args.screener is not None:
        print(f"\n=== Screener: {args.screener} ===")
        result = run_screener(filter_name=args.screener)
        _print_result("screener", result)

    elif args.tweets:
        ticker = args.tweets.upper()
        existing = load_valuation(ticker)
        if existing:
            tweets = run_social_media(existing, content_type="analysis")
        else:
            news = run_news_fetcher(ticker)
            tweets = run_social_media(news, content_type="news")
        for i, tweet in enumerate(tweets, 1):
            print(f"\n[{i}] {tweet}")

    elif args.article:
        print(run_content_writer(topic=args.article))

    elif args.query:
        run_pipeline(args.query)

    else:
        print("Sistema de inversion -- 'q' para salir, 'help' para ayuda\n")
        while True:
            try:
                user_input = input(">> ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nHasta luego.")
                break
            if not user_input:
                continue
            if user_input.lower() in ("q", "quit", "exit", "salir"):
                break
            if user_input.lower() == "help":
                parser.print_help()
                continue
            run_pipeline(user_input)


if __name__ == "__main__":
    main()
