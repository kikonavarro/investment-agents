"""
Message Queue — cola de mensajes entre Investment Bot y Claude Code.

Flujo:
  1. Investment Bot recibe mensaje de amigo → enqueue_message()
  2. Claude Code lee pendientes → get_pending()
  3. Claude Code procesa y responde → save_response() + send_response()
  4. Se marca como enviado → mark_sent()

Directorio: data/telegram_queue/
  inbox/    — mensajes pendientes y respondidos
  done/     — mensajes enviados (historial)
"""
import json
import os
from datetime import datetime
from pathlib import Path

QUEUE_DIR = Path(__file__).parent.parent / "data" / "telegram_queue"
INBOX_DIR = QUEUE_DIR / "inbox"
DONE_DIR = QUEUE_DIR / "done"


def _init():
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)


def enqueue_message(chat_id: str, user_name: str, text: str,
                    from_group: bool = False) -> str:
    """Encola un mensaje de Telegram. Retorna el msg_id."""
    _init()
    ts = datetime.now()
    msg_id = ts.strftime("%Y%m%d_%H%M%S") + f"_{chat_id}"
    msg = {
        "id": msg_id,
        "chat_id": chat_id,
        "user_name": user_name,
        "text": text,
        "from_group": from_group,
        "timestamp": ts.isoformat(),
        "status": "pending",
        "response": None,
    }
    path = INBOX_DIR / f"{msg_id}.json"
    path.write_text(json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8")
    return msg_id


def get_pending() -> list[dict]:
    """Retorna mensajes pendientes (sin respuesta)."""
    _init()
    msgs = []
    for f in sorted(INBOX_DIR.glob("*.json")):
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
            if msg.get("status") == "pending":
                msgs.append(msg)
        except (json.JSONDecodeError, Exception):
            continue
    return msgs


def save_response(msg_id: str, response: str):
    """Guarda la respuesta de Claude Code para un mensaje."""
    path = INBOX_DIR / f"{msg_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Mensaje {msg_id} no encontrado")
    msg = json.loads(path.read_text(encoding="utf-8"))
    msg["response"] = response
    msg["status"] = "responded"
    msg["responded_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8")


def send_response(msg_id: str) -> bool:
    """Envía la respuesta via Investment Bot y marca como enviado.
    Si falla, marca como send_failed y mantiene en inbox/ para reintento."""
    path = INBOX_DIR / f"{msg_id}.json"
    if not path.exists():
        return False

    msg = json.loads(path.read_text(encoding="utf-8"))
    if not msg.get("response"):
        return False

    # Enviar por Telegram
    from tools.telegram_bot import send_message, _load_config
    _, _, _, api_base = _load_config()
    success = send_message(api_base, msg["chat_id"], msg["response"])

    if success:
        mark_sent(msg_id)
        return True
    else:
        # Marcar como fallido, mantener en inbox/ para reintento
        msg["status"] = "send_failed"
        msg["retry_count"] = msg.get("retry_count", 0) + 1
        msg["failed_at"] = datetime.now().isoformat()
        path.write_text(json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [queue] Fallo al enviar {msg_id} (intento {msg['retry_count']})")
        return False


def get_failed() -> list[dict]:
    """Retorna mensajes con status send_failed."""
    _init()
    msgs = []
    for f in sorted(INBOX_DIR.glob("*.json")):
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
            if msg.get("status") == "send_failed":
                msgs.append(msg)
        except (json.JSONDecodeError, Exception):
            continue
    return msgs


def retry_failed(max_retries: int = 3) -> int:
    """Reintenta mensajes fallidos. Retorna número de mensajes reenviados con éxito."""
    failed = get_failed()
    sent = 0
    for msg in failed:
        if msg.get("retry_count", 0) >= max_retries:
            print(f"  [queue] {msg['id']} excede max reintentos ({max_retries}), saltando")
            continue
        if send_response(msg["id"]):
            sent += 1
    return sent


def mark_sent(msg_id: str):
    """Mueve mensaje a done/."""
    _init()
    src = INBOX_DIR / f"{msg_id}.json"
    if not src.exists():
        return
    msg = json.loads(src.read_text(encoding="utf-8"))
    msg["status"] = "sent"
    msg["sent_at"] = datetime.now().isoformat()
    dst = DONE_DIR / f"{msg_id}.json"
    dst.write_text(json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8")
    src.unlink()
