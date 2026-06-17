#!/usr/bin/env python3
"""
Watchdog del procesador de la bandeja. Lo dispara launchd cada ~5 min
(com.investment.inbox-watchdog.plist).

Avisa por Telegram (notifier.send_alert) si la cadena de procesamiento se rompe:
  1. El job del procesador no late (latido caducado) -> no está corriendo.
  2. Un mensaje lleva atascado sin procesar > N min -> la señal end-to-end más
     fiable (cubre login de Claude caducado, bug o cuelgue).

El aviso incluye la causa probable y el comando de recuperación, para que arreglarlo
sea leer y ejecutar. Anti-spam: un solo aviso por episodio (no repite cada 5 min).
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

HEARTBEAT = REPO / "data" / ".processor_heartbeat"
STATE = REPO / "data" / ".watchdog_alerted"   # marca de "ya avisé de este episodio"

# process_inbox.py refresca el latido cada 30s con un hilo de fondo MIENTRAS claude -p
# corre, así que un latido congelado vuelve a significar "muerto" (no "ocupado en una tesis
# larga"). Por eso el umbral puede ser bajo: detecta una caída real en minutos, sin falsos
# positivos en tesis largas. NO subirlo al nivel del timeout (retrasaría la detección real).
HEARTBEAT_MAX_AGE = 360   # 6 min (el procesador late cada 60s, y cada 30s durante un run)
PENDING_MAX_AGE = 3600    # 60 min: con 3 intentos x 30 min, un mensaje puede tardar legítimamente


def _heartbeat_age():
    """Segundos desde el último latido, o None si nunca ha latido."""
    try:
        return time.time() - float(HEARTBEAT.read_text().strip())
    except Exception:
        return None


def _oldest_pending_age():
    """Edad (s) del mensaje pendiente más antiguo. 0 si la cola está vacía."""
    try:
        from tools.message_queue import get_pending
        pending = get_pending()
    except Exception:
        return 0
    ages = []
    now = datetime.now(timezone.utc)
    for m in pending:
        ts = m.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ages.append((now - dt).total_seconds())
        except Exception:
            pass
    return max(ages) if ages else 0


def _alert(message: str):
    """Envía el aviso una sola vez por episodio (anti-spam)."""
    if STATE.exists():
        return
    STATE.write_text(str(time.time()))
    print(message)
    try:
        from tools import notifier
        notifier.send_alert(message)
    except Exception as e:
        print(f"[watchdog] no se pudo enviar alerta: {e}")


def _clear():
    """Todo sano: rearmar el aviso para el próximo episodio."""
    if STATE.exists():
        STATE.unlink()


def main():
    hb = _heartbeat_age()
    pending = _oldest_pending_age()

    # 1) ¿El job corre? (latido). Si nunca ha latido (None) no avisamos: puede ser
    #    primer arranque/instalación; el RunAtLoad lo creará enseguida.
    if hb is not None and hb > HEARTBEAT_MAX_AGE:
        mins = int(hb // 60)
        _alert(
            "⚠️ <b>Procesador de bandeja caído</b>\n"
            f"El job no late desde hace {mins} min (debería cada minuto).\n"
            "Recuperar: en el Mac, ejecuta <code>bandeja restart</code>."
        )
        return

    # 2) ¿Se está procesando? (mensaje atascado)
    if pending > PENDING_MAX_AGE:
        mins = int(pending // 60)
        _alert(
            "⚠️ <b>Bandeja atascada</b>\n"
            f"Hay un mensaje sin procesar hace {mins} min.\n"
            "Causa probable: login de Claude caducado.\n"
            "Recuperar: abre un terminal en el Mac y ejecuta <code>claude</code> "
            "una vez para re-loguear (o <code>bandeja restart</code> si fuera el job)."
        )
        return

    _clear()


if __name__ == "__main__":
    main()
