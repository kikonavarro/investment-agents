"""
scheduler.py — automatización de tareas periódicas (always-on).

Tareas programadas:
  - Cada 2h (08-20h):  news_scan() — RSS → SQLite → score con Haiku
  - Diaria (09:00):    daily_portfolio_check() — precios + alertas + Telegram
  - 3x/día:            price_update() — actualiza precios en Excel
  - 2x/día:            auto_tweet_generation() — mejor noticia → hilo → archivo
  - Semanal (lun 08h):  weekly_screener() — screener Graham + Telegram
  - Semanal (vie 18h):  weekly_portfolio_summary() — resumen cartera → Telegram
  - Semanal (sáb 10h):  weekly_revaluation() — re-analiza posiciones + alerta cambios

Uso:
    python scheduler.py                  # Loop continuo
    python scheduler.py --now daily      # Portfolio check
    python scheduler.py --now weekly     # Screener
    python scheduler.py --now news       # Fetch + score noticias
    python scheduler.py --now tweets     # Generar tweets
    python scheduler.py --now prices     # Actualizar precios
    python scheduler.py --now revalue    # Re-valorar posiciones
    python scheduler.py --now summary    # Resumen semanal
    python scheduler.py --now status     # Estado del sistema
"""
import sys
import json
import argparse
import logging
import traceback
from datetime import date, datetime
from pathlib import Path

import schedule
import time

from config.settings import TWEETS_DIR

# ─── Logging ────────────────────────────────────────────────────────────────────
LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "scheduler.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ─── Safe wrapper ────────────────────────────────────────────────────────────────

def _safe_run(task_fn):
    """Ejecuta una tarea capturando excepciones para no matar el loop."""
    try:
        return task_fn()
    except Exception:
        log.error(f"Error en {task_fn.__name__}:\n{traceback.format_exc()}")
        try:
            from tools.state_db import log_alert
            log_alert("ERROR", "", f"{task_fn.__name__}: {traceback.format_exc()[-200:]}")
        except Exception:
            pass
        return None


# ─── Tarea: Portfolio check (diaria) ─────────────────────────────────────────────

def daily_portfolio_check():
    """
    1. Actualiza precios de posiciones automáticas
    2. Calcula P&L actual
    3. Detecta alertas (target/stop loss alcanzado)
    4. Guarda log de alertas en fichero + SQLite
    """
    log.info("=== TAREA DIARIA: Portfolio check ===")

    from tools.excel_portfolio import get_portfolio_summary, update_prices
    from tools.financial_data import get_current_prices
    from tools.state_db import log_alert

    # Paso 1: Actualizar precios
    summary = get_portfolio_summary()
    auto_tickers = [
        p["name"] for p in summary["positions"] if p["source"] == "auto"
    ]

    if auto_tickers:
        log.info(f"Actualizando precios: {auto_tickers}")
        prices = get_current_prices(auto_tickers)
        update_prices(prices)
        log.info(f"Precios actualizados: {prices}")

    # Paso 2: Leer estado actualizado
    summary = get_portfolio_summary()
    total = summary["total_value"]
    pnl = summary["total_pnl_pct"]
    log.info(f"Cartera: valor={total:,.2f} | P&L={pnl:+.2f}%")

    # Paso 3: Detectar y registrar alertas
    alerts = _check_alerts(summary)
    if alerts:
        log.warning(f"ALERTAS ({len(alerts)}):")
        for alert in alerts:
            log.warning(f"  {alert}")
            # Persistir en SQLite
            log_alert("PORTFOLIO", alert.split("]")[0].strip("["), alert)
        _save_alerts(alerts)
        # Notificar por Telegram
        from tools.notifier import notify_portfolio_alerts
        notify_portfolio_alerts(alerts)
    else:
        log.info("Sin alertas activas.")

    log.info("=== Tarea diaria completada ===\n")
    return alerts


def _check_alerts(summary: dict) -> list[str]:
    """
    Revisa cada posición y genera alertas cuando:
    - Precio >= target (TOMAR BENEFICIOS)
    - Precio <= stop loss (REVISAR POSICION)
    - Fondo manual sin actualizar >30 dias
    """
    alerts = []
    for pos in summary["positions"]:
        alert = pos.get("alert")
        if alert:
            name = pos["name"]
            pnl = pos["pnl_pct"]
            alerts.append(f"[{alert}] {name} | P&L: {pnl:+.1f}%")
    return alerts


def _save_alerts(alerts: list[str]):
    """Guarda las alertas en un fichero de log diario."""
    alerts_file = LOG_DIR / f"alerts_{date.today().isoformat()}.txt"
    with open(alerts_file, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().strftime('%H:%M:%S')}]\n")
        for alert in alerts:
            f.write(f"  {alert}\n")
    log.info(f"Alertas guardadas en {alerts_file}")


# ─── Tarea: Price update (3x/dia) ───────────────────────────────────────────────

def price_update():
    """Actualiza precios en Excel sin alertas ni Claude. Solo yfinance."""
    log.info("--- Actualización de precios ---")

    from tools.excel_portfolio import read_portfolio, update_prices
    from tools.financial_data import get_current_prices

    positions = read_portfolio()
    auto_tickers = [
        p["ticker"] for p in positions
        if p.get("source") == "auto" and p.get("ticker")
    ]

    if not auto_tickers:
        log.info("Sin posiciones auto para actualizar.")
        return

    prices = get_current_prices(auto_tickers)
    if prices:
        update_prices(prices)
        log.info(f"Precios actualizados: {prices}")
    else:
        log.warning("No se obtuvieron precios.")


# ─── Tarea: News scan (cada 2h) ─────────────────────────────────────────────────

def news_scan():
    """
    1. Lee tickers de cartera + watchlist
    2. Fetch RSS para cada ticker
    3. Guarda en SQLite (skip duplicados por URL)
    4. Puntua noticias nuevas con Haiku (batch)
    """
    log.info("--- News scan ---")

    from tools.excel_portfolio import read_portfolio, read_watchlist
    from tools.news_fetcher import get_multi_ticker_news
    from tools.state_db import init_db, mark_news_processed

    init_db()

    # Recopilar tickers
    positions = read_portfolio()
    watchlist = read_watchlist()
    tickers = set()
    for p in positions:
        if p.get("ticker"):
            tickers.add(p["ticker"])
    for w in watchlist:
        if w.get("ticker"):
            tickers.add(w["ticker"])

    if not tickers:
        log.info("Sin tickers para monitorizar.")
        return

    log.info(f"Escaneando noticias para {len(tickers)} tickers: {sorted(tickers)}")

    # Fetch RSS
    all_news = get_multi_ticker_news(list(tickers), max_per_ticker=5)

    new_count = 0
    for ticker, items in all_news.items():
        for item in items:
            url = item.get("url", "").strip()
            if not url:
                continue
            news_id = mark_news_processed(
                url=url,
                ticker=ticker,
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                pub_date=item.get("date", ""),
            )
            if news_id is not None:
                new_count += 1

    log.info(f"Noticias nuevas guardadas: {new_count}")

    # Puntuar noticias sin score
    if new_count > 0:
        _score_news_batch()


def _score_news_batch():
    """Puntua noticias sin score con reglas por keywords (sin API, sin coste)."""
    from tools.state_db import get_unscored_news, update_news_score

    # Keywords de alto impacto para value investing
    HIGH_SCORE = {
        10: ["bankruptcy", "quiebra", "fraud", "fraude", "restatement"],
        9: ["acquisition", "adquisicion", "merger", "fusión", "takeover", "buyout",
            "activist investor", "proxy fight"],
        8: ["earnings beat", "earnings miss", "guidance raise", "guidance cut",
            "dividend cut", "dividend increase", "stock split", "buyback",
            "share repurchase", "ceo resign", "ceo fired", "cfo resign"],
        7: ["upgrade", "downgrade", "price target", "precio objetivo",
            "rating change", "beat estimates", "miss estimates",
            "revenue growth", "profit warning", "restructuring"],
        6: ["earnings", "resultados", "quarterly results", "annual report",
            "10-K", "10-Q", "SEC filing", "insider buying", "insider selling",
            "new product", "patent", "regulation", "regulación"],
    }

    unscored = get_unscored_news()
    if not unscored:
        return

    scored_count = 0
    for news in unscored:
        title_lower = (news.get("title", "") + " " + news.get("summary", "")).lower()
        score = 3  # default: ruido de mercado

        for pts, keywords in HIGH_SCORE.items():
            if any(kw in title_lower for kw in keywords):
                score = pts
                break

        update_news_score(news["id"], score)
        scored_count += 1

    log.info(f"Noticias puntuadas (por reglas): {scored_count}")


# ─── Tarea: Auto tweet generation (2x/dia) ──────────────────────────────────────

def auto_tweet_generation():
    """
    1. Chequea cap diario (max 2)
    2. Busca mejor noticia no tuiteada (score >= 6)
    3. Encola para Claude Code (Opus) en vez de llamar a la API
    """
    log.info("--- Auto tweet generation ---")

    from tools.state_db import (
        init_db, get_today_tweet_count, get_best_untweeted_news,
    )
    from tools.message_queue import enqueue_message
    from tools.notifier import is_enabled

    init_db()

    today_count = get_today_tweet_count()
    if today_count >= 2:
        log.info(f"Cap diario alcanzado ({today_count}/2 hilos). Saltando.")
        return

    news = get_best_untweeted_news(min_score=6)
    if not news:
        log.info("Sin noticias de alto interes para tuitear.")
        return

    log.info(f"Noticia para tweets: [{news['ticker']}] {news['title'][:60]}...")

    # Encolar como mensaje para Claude Code
    msg_text = (
        f"[SCHEDULER] Genera un hilo de tweets sobre esta noticia:\n"
        f"Ticker: {news['ticker']}\n"
        f"Titular: {news['title']}\n"
        f"Resumen: {news.get('summary', 'N/A')}\n"
        f"Score: {news['interest_score']}/10\n"
        f"News ID: {news['id']}"
    )

    # Encolar en la cola del owner para que Opus lo procese
    import os
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).parent / ".env")
    owner_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if owner_chat_id:
        enqueue_message(owner_chat_id, "SCHEDULER", msg_text, from_group=False)
        log.info(f"Encolado para Opus: tweet sobre {news['ticker']}")
    else:
        log.warning("Sin TELEGRAM_CHAT_ID, no se puede encolar.")


def _save_tweets_to_file(ticker: str, tweets: list[str]) -> Path:
    """Escribe hilo formateado en txt."""
    TWEETS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    # Evitar colisiones si hay mas de uno por ticker/dia
    existing = list(TWEETS_DIR.glob(f"{today}_{ticker}*.txt"))
    suffix = f"_{len(existing) + 1}" if existing else ""
    file_path = TWEETS_DIR / f"{today}_{ticker}{suffix}.txt"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# Hilo Twitter — {ticker} — {today}\n")
        f.write(f"# Generado automaticamente por investment-agents\n\n")
        for i, tweet in enumerate(tweets, 1):
            f.write(f"--- Tweet {i}/{len(tweets)} ---\n")
            f.write(f"{tweet}\n\n")

    return file_path


# ─── Tarea semanal: screener ────────────────────────────────────────────────────

def weekly_screener():
    """
    1. Corre solo la parte Python del screener (filtros cuantitativos)
    2. Encola resultados para que Claude Code (Opus) haga el ranking cualitativo
    """
    log.info("=== TAREA SEMANAL: Screener ===")

    from tools.screener_engine import run_screen
    from tools.message_queue import enqueue_message

    candidates = run_screen("graham_default", ["SP500"])

    if not candidates:
        log.info("Ninguna empresa pasó los filtros.")
        return

    top15 = candidates[:15]
    log.info(f"Candidatas encontradas: {len(candidates)}, top 15 para ranking")

    # Formatear resumen para Opus
    lines = [f"[SCHEDULER] Screener semanal Graham — {len(candidates)} pasaron filtros. Top 15:"]
    for i, c in enumerate(top15, 1):
        ticker = c.get("ticker", "?")
        pe = c.get("pe_ratio", 0)
        pb = c.get("pb_ratio", 0)
        dy = c.get("dividend_yield", 0)
        mc = c.get("market_cap", 0)
        lines.append(
            f"  {i:2d}. {ticker:8s} | P/E={pe:.1f} | P/B={pb:.1f} | DY={dy:.1%} | MCap={mc/1e9:.1f}B"
        )
    lines.append("\nHaz el ranking cualitativo (moat, calidad del negocio, riesgos) y envía el top 5.")

    import os
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).parent / ".env")
    owner_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if owner_chat_id:
        enqueue_message(owner_chat_id, "SCHEDULER", "\n".join(lines), from_group=False)
        log.info("Encolado para Opus: ranking cualitativo del screener")

    # Notificar datos crudos por Telegram
    from tools.notifier import send_alert
    header = f"🔍 <b>SCREENER SEMANAL</b> — graham_default\n{len(candidates)} pasaron filtros\n\n"
    body = "\n".join(f"  {i}. <b>{c.get('ticker','?')}</b> P/E={c.get('pe_ratio',0):.1f}"
                     for i, c in enumerate(top15[:5], 1))
    send_alert(header + body + "\n\n⏳ Opus está preparando el ranking cualitativo...")

    log.info("=== Screener completado ===\n")
    return candidates


# ─── Tarea semanal: re-valoración de posiciones ──────────────────────────────────

def weekly_revaluation():
    """
    Re-ejecuta el analyst para cada posición de la cartera.
    Compara el nuevo fair value con el anterior y alerta si cambia >10%.
    """
    log.info("=== TAREA SEMANAL: Re-valoración ===")

    from tools.excel_portfolio import read_portfolio
    from agents.analyst import run_analyst, load_valuation, load_history

    positions = read_portfolio()
    auto_tickers = [
        p["ticker"] for p in positions
        if p.get("source") == "auto" and p.get("ticker")
    ]

    if not auto_tickers:
        log.info("Sin posiciones auto para re-valorar.")
        return

    from tools.notifier import notify_revaluation

    for ticker in auto_tickers:
        log.info(f"Re-valorando {ticker}...")
        try:
            # Guardar precio anterior del historial
            history = load_history(ticker)
            old_price = history[-1]["current_price"] if history else None

            # Re-ejecutar analyst (genera nuevo JSON + historial)
            result = run_analyst(ticker)
            new_price = result.get("current_price", 0)

            # Comparar con valoración anterior
            if old_price and old_price > 0:
                change_pct = (new_price / old_price - 1) * 100
                if abs(change_pct) > 10:
                    currency = result.get("currency", "$")
                    notify_revaluation(ticker, old_price, new_price, change_pct, currency)
                    log.warning(f"  {ticker}: precio cambió {change_pct:+.1f}%")
                else:
                    log.info(f"  {ticker}: sin cambio significativo ({change_pct:+.1f}%)")

        except Exception:
            log.error(f"  Error re-valorando {ticker}:\n{traceback.format_exc()}")

    log.info("=== Re-valoración completada ===\n")


# ─── Tarea semanal: resumen de cartera ──────────────────────────────────────────

def weekly_portfolio_summary():
    """Envía un resumen semanal del estado de la cartera por Telegram."""
    log.info("=== TAREA SEMANAL: Resumen de cartera ===")

    from tools.excel_portfolio import get_portfolio_summary
    from tools.notifier import notify_weekly_summary

    summary = get_portfolio_summary()
    notify_weekly_summary(summary)

    total = summary.get("total_value", 0)
    pnl = summary.get("total_pnl_pct", 0)
    log.info(f"Resumen enviado: valor={total:,.2f} | P&L={pnl:+.2f}%")
    log.info("=== Resumen completado ===\n")


# ─── Status ──────────────────────────────────────────────────────────────────────

def _print_scheduler_status():
    """Muestra stats del sistema desde SQLite."""
    from tools.state_db import init_db, get_news_stats, get_today_alerts

    init_db()
    stats = get_news_stats(days=7)
    alerts = get_today_alerts()

    print("\n╔══════════════════════════════════════╗")
    print("║     SCHEDULER STATUS                 ║")
    print("╠══════════════════════════════════════╣")
    print(f"║ Noticias (7d):  {stats['total_news']:>5}               ║")
    print(f"║ Puntuadas:      {stats['scored_news']:>5}               ║")
    print(f"║ Alto interes:   {stats['high_interest']:>5} (score>=6)    ║")
    print(f"║ Tuiteadas:      {stats['tweeted']:>5}               ║")
    print(f"║ Tweets hoy:     {stats['tweets_today']:>5} / 2            ║")
    print(f"║ Alertas hoy:    {stats['alerts_today']:>5}               ║")
    print("╚══════════════════════════════════════╝")

    if alerts:
        print("\nAlertas de hoy:")
        for a in alerts:
            print(f"  [{a['alert_type']}] {a['ticker']} — {a['message'][:60]}")
    print()


# ─── Configuracion del scheduler ────────────────────────────────────────────────

def setup_schedule():
    """Registra todas las tareas en el scheduler."""
    # News scan: cada 2h de 08 a 20h
    for hour in ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]:
        schedule.every().day.at(hour).do(lambda: _safe_run(news_scan))
    log.info("Programado: news_scan cada 2h (08-20h)")

    # Portfolio check: diario 09:00
    schedule.every().day.at("09:00").do(lambda: _safe_run(daily_portfolio_check))
    log.info("Programado: daily_portfolio_check a las 09:00")

    # Price update: 3x/dia
    for hour in ["09:30", "13:30", "17:30"]:
        schedule.every().day.at(hour).do(lambda: _safe_run(price_update))
    log.info("Programado: price_update a las 09:30, 13:30, 17:30")

    # Auto tweet generation: 2x/dia
    for hour in ["10:30", "17:30"]:
        schedule.every().day.at(hour).do(lambda: _safe_run(auto_tweet_generation))
    log.info("Programado: auto_tweet_generation a las 10:30, 17:30")

    # Screener semanal: lunes 08:00
    schedule.every().monday.at("08:00").do(lambda: _safe_run(weekly_screener))
    log.info("Programado: weekly_screener los lunes a las 08:00")

    # Re-valoración semanal: sábado 10:00 (mercado cerrado, sin interferir)
    schedule.every().saturday.at("10:00").do(lambda: _safe_run(weekly_revaluation))
    log.info("Programado: weekly_revaluation los sábados a las 10:00")

    # Resumen semanal: viernes 18:00
    schedule.every().friday.at("18:00").do(lambda: _safe_run(weekly_portfolio_summary))
    log.info("Programado: weekly_portfolio_summary los viernes a las 18:00")


def run_loop():
    """Loop principal del scheduler. Corre indefinidamente."""
    from tools.state_db import init_db
    init_db()

    setup_schedule()
    log.info("Scheduler iniciado. Ctrl+C para detener.")

    # Mostrar proximas ejecuciones
    for job in sorted(schedule.jobs, key=lambda j: j.next_run):
        log.info(f"  Proxima: {job.next_run.strftime('%Y-%m-%d %H:%M')} — {job.job_func.__name__}")

    _print_scheduler_status()

    while True:
        schedule.run_pending()
        time.sleep(30)


# ─── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scheduler de tareas de inversion")
    parser.add_argument(
        "--now",
        choices=["daily", "weekly", "news", "tweets", "prices", "revalue", "summary", "status"],
        help="Ejecuta una tarea inmediatamente sin esperar al horario",
    )
    args = parser.parse_args()

    if args.now == "daily":
        log.info("Ejecutando tarea diaria manualmente...")
        alerts = daily_portfolio_check()
        if alerts:
            print("\nALERTAS:")
            for a in alerts:
                print(f"  {a}")
        else:
            print("\nSin alertas.")

    elif args.now == "weekly":
        log.info("Ejecutando screener manualmente...")
        weekly_screener()

    elif args.now == "news":
        log.info("Ejecutando news scan manualmente...")
        from tools.state_db import init_db
        init_db()
        news_scan()
        _print_scheduler_status()

    elif args.now == "tweets":
        log.info("Ejecutando tweet generation manualmente...")
        from tools.state_db import init_db
        init_db()
        auto_tweet_generation()

    elif args.now == "prices":
        log.info("Ejecutando price update manualmente...")
        price_update()

    elif args.now == "revalue":
        log.info("Ejecutando re-valoración manualmente...")
        weekly_revaluation()

    elif args.now == "summary":
        log.info("Ejecutando resumen semanal manualmente...")
        weekly_portfolio_summary()

    elif args.now == "status":
        _print_scheduler_status()

    else:
        run_loop()


if __name__ == "__main__":
    main()
