"""
main.py — CLI del sistema multi-agente de inversion.

Uso:
    python main.py                        # Modo interactivo
    python main.py "Analiza AAPL"         # Modo directo
    python main.py --analyst AAPL         # Valoracion completa (Excel + JSON)
    python main.py --thesis AAPL          # Valoracion + tesis
    python main.py --deep AAPL            # Analisis profundo (4 agentes especializados + tesis)
    python main.py --portfolio status     # Estado de cartera
    python main.py --screener             # Buscar ideas value
"""
import sys
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import orchestrate
from agents.analyst import run_analyst, load_valuation, quick_summary, load_history
from agents.base import AgentError, reset_tracker, print_tracker_summary
from agents.news_fetcher import run_news_fetcher
from agents.thesis_writer import run_thesis_writer
from agents.social_media import run_social_media
from agents.portfolio_tracker import run_portfolio_tracker
from agents.content_writer import run_content_writer
from agents.screener import run_screener
from agents.business_model import run_business_model
from agents.moat_analyst import run_moat_analyst
from agents.capital_allocation import run_capital_allocation
from agents.risk_analyst import run_risk_analyst
from tools.document_generator import save_analysis_json, save_screener_report
from tools.quality_gates import validate_valuation, print_quality_report
from tools.email_sender import send_thesis_email

AGENT_MAP = {
    "analyst": run_analyst,
    "news_fetcher": run_news_fetcher,
    "thesis_writer": run_thesis_writer,
    "social_media": run_social_media,
    "portfolio_tracker": run_portfolio_tracker,
    "content_writer": run_content_writer,
    "screener": run_screener,
    "email_sender": send_thesis_email,
}


def _is_dependent(step: dict) -> bool:
    """Comprueba si un step depende del output de otro agente."""
    # email_sender siempre va después de thesis_writer
    if step.get("agent") == "email_sender":
        return True
    inp = str(step.get("input", "")).lower()
    return inp.startswith("from_")


def _split_waves(steps: list[dict]) -> list[list[dict]]:
    """
    Agrupa steps en olas de ejecución.
    Ola 1: steps independientes (pueden ir en paralelo).
    Ola 2+: steps dependientes (secuenciales, en orden).
    """
    independent = [s for s in steps if not _is_dependent(s)]
    dependent = [s for s in steps if _is_dependent(s)]
    waves = []
    if independent:
        waves.append(independent)
    # Los dependientes van uno a uno (respetando orden del orquestador)
    for s in dependent:
        waves.append([s])
    return waves


def _execute_step(step: dict, context: dict) -> tuple[str, any, Exception | None]:
    """Ejecuta un step individual. Devuelve (agent_name, result, error)."""
    agent_name = step["agent"]
    agent_input = step["input"]
    resolved_input = _resolve_input(agent_input, agent_name, context)
    try:
        result = _call_agent(agent_name, resolved_input)
        return agent_name, result, None
    except Exception as e:
        return agent_name, None, e


def run_pipeline(user_input: str) -> dict:
    """Ejecuta el pipeline: orquestador -> agentes -> resultados (con paralelización)."""
    reset_tracker()
    print(f"\nInstruccion: {user_input}")
    steps = orchestrate(user_input)
    print(f"Plan: {json.dumps(steps, ensure_ascii=False)}\n")

    # Filtrar agentes desconocidos
    valid_steps = []
    for step in steps:
        if step["agent"] not in AGENT_MAP:
            print(f"[!] Agente desconocido: {step['agent']}")
        else:
            valid_steps.append(step)

    # Si hay email_sender y la tesis ya existe en disco, saltar thesis_writer
    has_email = any(s["agent"] == "email_sender" for s in valid_steps)
    if has_email:
        email_step = next(s for s in valid_steps if s["agent"] == "email_sender")
        ticker_for_email = email_step.get("input", {}).get("ticker", "") if isinstance(email_step.get("input"), dict) else ""
        if ticker_for_email:
            from agents.analyst import _clean_ticker
            from config.settings import VALUATIONS_DIR
            clean = _clean_ticker(ticker_for_email)
            md_path = VALUATIONS_DIR / clean / f"{clean}_tesis_inversion.md"
            if md_path.exists():
                # Tesis ya existe — saltar thesis_writer, ir directo a email
                valid_steps = [s for s in valid_steps if s["agent"] != "thesis_writer"]
                print(f"  [email] Tesis de {ticker_for_email} ya existe, enviando directamente.")

    context = {"_steps": steps, "_errors": []}
    waves = _split_waves(valid_steps)

    for i, wave in enumerate(waves):
        if len(wave) == 1:
            # Un solo step: ejecutar directamente
            step = wave[0]
            print(f"--- {step['agent'].upper()} ---")
            name, result, error = _execute_step(step, context)
            if error:
                context["_errors"].append({"agent": name, "error": str(error)})
                print(f"  [!] {name} falló: {error}")
                print(f"  [!] Continuando con los demás agentes...")
            else:
                context[f"{name}_output"] = result
                _print_result(name, result)
        else:
            # Múltiples steps: ejecutar en paralelo
            print(f"  [paralelo] Ejecutando {len(wave)} agentes en paralelo: "
                  f"{', '.join(s['agent'] for s in wave)}")
            with ThreadPoolExecutor(max_workers=len(wave)) as executor:
                futures = {
                    executor.submit(_execute_step, step, context): step
                    for step in wave
                }
                for future in as_completed(futures):
                    name, result, error = future.result()
                    print(f"\n--- {name.upper()} ---")
                    if error:
                        context["_errors"].append({"agent": name, "error": str(error)})
                        print(f"  [!] {name} falló: {error}")
                    else:
                        context[f"{name}_output"] = result
                        _print_result(name, result)

    if context["_errors"]:
        print(f"\n⚠ Pipeline completado con {len(context['_errors'])} error(es):")
        for err in context["_errors"]:
            print(f"  - {err['agent']}: {err['error']}")

    print_tracker_summary()
    return context


def _resolve_input(agent_input, agent_name, context):
    s = str(agent_input).lower() if isinstance(agent_input, str) else ""
    if "from_analyst" in s or s == "from_analyst":
        return context.get("analyst_output", {})
    if agent_input == "from_screener_top3":
        top5 = context.get("screener_output", {}).get("top_5", [])
        return [t["ticker"] for t in top5[:3]]
    if "from_news" in s or s == "from_news":
        return context.get("news_fetcher_output", {})
    # email_sender: pasar thesis_md del contexto si existe
    if agent_name == "email_sender" and isinstance(agent_input, dict):
        thesis_output = context.get("thesis_writer_output")
        if isinstance(thesis_output, str) and thesis_output:
            agent_input["thesis_md"] = thesis_output
    return agent_input


def _call_agent(agent_name, agent_input):
    fn = AGENT_MAP[agent_name]
    if agent_name == "analyst":
        if isinstance(agent_input, list):
            results = [fn(t) for t in agent_input]
            for r in results:
                print_quality_report(validate_valuation(r))
            return results
        result = fn(str(agent_input))
        print_quality_report(validate_valuation(result))
        return result
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
    elif agent_name == "email_sender":
        if isinstance(agent_input, dict):
            return fn(
                ticker=agent_input.get("ticker", ""),
                recipient=agent_input.get("email"),
                thesis_md=agent_input.get("thesis_md"),
            )
        return fn(ticker=str(agent_input))
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
    elif agent_name == "email_sender":
        if isinstance(result, dict):
            if result.get("success"):
                print(f"  ✉ {result.get('message', 'Email enviado')}")
            else:
                print(f"  [!] {result.get('message', 'Error enviando email')}")
    elif isinstance(result, str):
        print(result)
    elif isinstance(result, dict):
        print(json.dumps(result, indent=2, ensure_ascii=False))


def _print_specialized(name: str, result: dict):
    """Imprime resumen breve de un agente especializado."""
    score = result.get(f"{name}_score", result.get("moat_score", result.get("risk_score", "?")))
    summary = result.get("summary", "")
    # Extraer el rating/nivel principal
    rating = (result.get(f"{name}_rating") or result.get("moat_rating")
              or result.get("overall_risk_level") or result.get("revenue_quality") or "")
    if rating:
        print(f"  Score: {score}/10 | Rating: {rating}")
    else:
        print(f"  Score: {score}/10")
    if summary:
        print(f"  {summary[:200]}")


def _save_deep_analysis(ticker: str, specialized: dict):
    """Guarda el análisis especializado en la carpeta de valoración."""
    from agents.analyst import _clean_ticker
    from config.settings import VALUATIONS_DIR
    folder = VALUATIONS_DIR / _clean_ticker(ticker)
    if not folder.exists():
        return
    path = folder / f"{_clean_ticker(ticker)}_deep_analysis.json"
    path.write_text(json.dumps(specialized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Análisis profundo guardado: {path}")


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
    parser.add_argument("--deep", metavar="TICKER",
                        help="Analisis profundo: valoracion + 4 agentes especializados + tesis")
    parser.add_argument("--portfolio", metavar="ACTION", default=None,
                        help="Gestiona cartera: status|update_prices|...")
    parser.add_argument("--screener", metavar="FILTER", nargs="?", const="graham_default",
                        help="Busca ideas value")
    parser.add_argument("--tweets", metavar="TICKER", help="Genera tweets")
    parser.add_argument("--article", metavar="TOPIC", help="Escribe articulo Substack")
    parser.add_argument("--history", metavar="TICKER",
                        help="Muestra historial de valoraciones de un ticker")
    parser.add_argument("--data-only", action="store_true",
                        help="Solo ejecuta Python (datos/Excel/filtros), sin llamadas API de Claude")
    parser.add_argument("--fresh", action="store_true",
                        help="Forzar descarga de datos frescos (ignorar cache)")

    args = parser.parse_args()

    # Activar modo data-only si se pasa el flag
    if args.data_only:
        from config import settings as _settings
        _settings.DATA_ONLY_MODE = True
        print("[modo data-only] Sin llamadas API de Claude\n")

    # Forzar datos frescos (ignorar caché)
    if args.fresh:
        from config import settings as _settings
        _settings.FORCE_FRESH = True
        print("[modo fresh] Ignorando caché, descarga forzada\n")

    reset_tracker()

    if args.analyst:
        for ticker in args.analyst:
            t = ticker.upper()
            print(f"\n=== Valoracion: {t} ===")
            result = run_analyst(t)
            print_quality_report(validate_valuation(result))
            _print_quick_summary(result)

    elif args.deep:
        ticker = args.deep.upper()
        # 1. Valoración base
        existing = load_valuation(ticker)
        if existing is None:
            print(f"\n=== Valoracion: {ticker} ===")
            existing = run_analyst(ticker)
        else:
            print(f"\n=== Usando valoracion existente de {ticker} ===")

        # 1b. Quality gate
        qg = validate_valuation(existing)
        print_quality_report(qg)
        if qg["confidence"] == "low":
            print("\n  [!] Confianza BAJA en los datos. Los análisis pueden ser poco fiables.")
            print("  [!] Considera re-ejecutar con --fresh o verificar los datos manualmente.")

        # 2. Agentes especializados (en paralelo)
        print(f"\n  Ejecutando 4 agentes especializados en paralelo...")
        specialized = {}
        agents_to_run = [
            ("business_model", run_business_model),
            ("moat", run_moat_analyst),
            ("capital_allocation", run_capital_allocation),
            ("risk", run_risk_analyst),
        ]
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(fn, ticker): name for name, fn in agents_to_run}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    specialized[name] = future.result()
                    print(f"\n--- {name.upper().replace('_', ' ')} ---")
                    _print_specialized(name, specialized[name])
                except Exception as e:
                    print(f"\n--- {name.upper().replace('_', ' ')} ---")
                    print(f"  [!] {name} falló: {e}")

        # 3. Guardar análisis especializado junto a la valoración
        _save_deep_analysis(ticker, specialized)

        # 4. Tesis enriquecida
        print(f"\n=== Redactando tesis enriquecida: {ticker} ===")
        thesis = run_thesis_writer(ticker)
        print(thesis)

    elif args.thesis:
        ticker = args.thesis.upper()
        existing = load_valuation(ticker)
        if existing is None:
            print(f"\nNo existe valoracion previa para {ticker}. Ejecutando primero...")
            existing = run_analyst(ticker)
        print_quality_report(validate_valuation(existing))
        print(f"\n=== Redactando tesis: {ticker} ===")
        thesis = run_thesis_writer(ticker)
        print(thesis)

    elif args.history:
        ticker = args.history.upper()
        history = load_history(ticker)
        if not history:
            print(f"\nNo hay historial para {ticker}.")
        else:
            print(f"\n=== Historial de {ticker} ({len(history)} valoracion(es)) ===\n")
            print(f"  {'Fecha':12s} {'Precio':>10s} {'Growth Y1':>10s} "
                  f"{'WACC':>8s} {'TV':>6s} {'Margen bruto':>12s}")
            print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*8} {'-'*6} {'-'*12}")
            for h in history:
                cur = h.get("currency", "$")
                price = h.get("current_price", 0)
                g1 = h.get("growth_y1_base", 0)
                wacc = h.get("wacc_base", 0)
                tv = h.get("tv_base", 0)
                gm = h.get("gross_margin", 0)
                print(f"  {h['date']:12s} {cur}{price:>9,.2f} {g1:>9.1%} "
                      f"{wacc:>7.1%} {tv:>5.0f}x {gm:>11.1%}")

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

    # Resumen de costes para comandos directos (run_pipeline lo imprime internamente)
    direct_command = (args.analyst or args.deep or args.thesis
                      or args.portfolio is not None
                      or args.screener is not None or args.tweets or args.article)
    if direct_command:
        print_tracker_summary()


if __name__ == "__main__":
    main()
