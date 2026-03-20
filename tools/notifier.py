"""
Notifier — envío de alertas por Telegram.
Abstrae el envío para que el scheduler no dependa de los detalles del bot.
Si Telegram no está configurado, solo loguea.
"""
import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_config = None


def _get_config():
    """Carga config de Telegram (lazy, una sola vez)."""
    global _config
    if _config is not None:
        return _config

    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    group_id = os.environ.get("TELEGRAM_GROUP_ID", "")

    _config = {
        "token": token,
        "chat_id": chat_id,
        "group_id": group_id,
        "api_base": f"https://api.telegram.org/bot{token}" if token else "",
        "enabled": bool(token and (chat_id or group_id)),
    }
    return _config


def is_enabled() -> bool:
    """True si Telegram está configurado."""
    return _get_config()["enabled"]


def send_alert(message: str, use_group: bool = False):
    """
    Envía un mensaje de alerta. Si Telegram no está configurado, solo loguea.

    Args:
        message: Texto a enviar (puede ser HTML o plain text).
        use_group: Si True, envía al grupo en vez del chat privado.
    """
    log.info(f"[alerta] {message[:100]}...")

    cfg = _get_config()
    if not cfg["enabled"]:
        log.debug("[notifier] Telegram no configurado, alerta solo en log.")
        return

    chat_id = cfg["group_id"] if use_group and cfg["group_id"] else cfg["chat_id"]
    if not chat_id:
        return

    try:
        from tools.telegram_bot import send_message
        send_message(cfg["api_base"], chat_id, message, html=True)
    except Exception as e:
        log.error(f"[notifier] Error enviando Telegram: {e}")


# --- Mensajes predefinidos ---

def notify_portfolio_alerts(alerts: list[str]):
    """Envía alertas de portfolio por Telegram."""
    if not alerts:
        return
    header = f"⚠️ <b>ALERTAS CARTERA</b> ({len(alerts)})\n\n"
    body = "\n".join(f"  • {a}" for a in alerts)
    send_alert(header + body)


def notify_screener_results(candidates: list[dict], filter_name: str = ""):
    """Envía top candidatos del screener por Telegram."""
    if not candidates:
        return
    header = f"🔍 <b>SCREENER</b> — {filter_name}\n"
    header += f"Top {len(candidates)} candidatas:\n\n"
    lines = []
    for i, c in enumerate(candidates, 1):
        ticker = c.get("ticker", "?")
        reason = c.get("reason", "")[:60]
        lines.append(f"  {i}. <b>{ticker}</b> — {reason}")
    send_alert(header + "\n".join(lines))


def notify_fair_value_cross(ticker: str, current_price: float,
                            fair_value: float, direction: str, currency: str = "$"):
    """Alerta cuando el precio cruza el fair value."""
    emoji = "🟢" if direction == "below" else "🔴"
    action = "POR DEBAJO del" if direction == "below" else "POR ENCIMA del"
    msg = (f"{emoji} <b>FAIR VALUE CRUZADO</b>\n\n"
           f"<b>{ticker}</b> cotiza {action} fair value\n"
           f"  Precio: {currency}{current_price:,.2f}\n"
           f"  Fair value (base): {currency}{fair_value:,.2f}\n"
           f"  Diferencia: {(current_price/fair_value - 1):+.1%}")
    send_alert(msg)


def notify_weekly_summary(summary: dict):
    """Envía resumen semanal de la cartera."""
    total = summary.get("total_value", 0)
    pnl = summary.get("total_pnl_pct", 0)
    positions = summary.get("positions", [])

    emoji = "📈" if pnl >= 0 else "📉"
    header = (f"📊 <b>RESUMEN SEMANAL</b>\n\n"
              f"  Valor total: ${total:,.2f}\n"
              f"  P&amp;L: {emoji} {pnl:+.2f}%\n\n")

    lines = []
    for p in positions:
        name = p.get("name", "?")[:15]
        p_pnl = p.get("pnl_pct", 0)
        icon = "🟢" if p_pnl >= 0 else "🔴"
        lines.append(f"  {icon} {name:15s} {p_pnl:+6.1f}%")

    send_alert(header + "\n".join(lines))


def notify_revaluation(ticker: str, old_price: float, new_price: float,
                       change_pct: float, currency: str = "$"):
    """Alerta cuando una re-valoración muestra cambio significativo."""
    emoji = "📈" if change_pct >= 0 else "📉"
    msg = (f"{emoji} <b>RE-VALORACIÓN</b>: {ticker}\n\n"
           f"  Fair value anterior: {currency}{old_price:,.2f}\n"
           f"  Fair value nuevo: {currency}{new_price:,.2f}\n"
           f"  Cambio: {change_pct:+.1f}%")
    send_alert(msg)
