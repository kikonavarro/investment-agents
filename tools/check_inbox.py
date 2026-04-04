#!/usr/bin/env python3
"""
check_inbox.py — CLI para que Claude Code gestione la cola de mensajes.

Uso:
    python tools/check_inbox.py                         # Ver mensajes pendientes
    python tools/check_inbox.py respond <msg_id> <file> # Responder con contenido de archivo
    python tools/check_inbox.py respond <msg_id> --text "respuesta"  # Responder inline
    python tools/check_inbox.py send <msg_id>           # Enviar respuesta guardada
    python tools/check_inbox.py send-all                # Enviar todas las respuestas pendientes
"""
import sys
import argparse
from pathlib import Path

# Asegurar imports desde raíz del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.message_queue import get_pending, get_failed, save_response, send_response, retry_failed, INBOX_DIR


def show_pending():
    """Muestra mensajes pendientes."""
    pending = get_pending()
    if not pending:
        print("No hay mensajes pendientes.")
        return

    print(f"\n{'='*60}")
    print(f"  MENSAJES PENDIENTES ({len(pending)})")
    print(f"{'='*60}\n")

    for msg in pending:
        ts = msg["timestamp"][:19].replace("T", " ")
        group = " [GRUPO]" if msg.get("from_group") else ""
        print(f"  ID: {msg['id']}")
        print(f"  De: {msg['user_name']}{group}")
        print(f"  Hora: {ts}")
        print(f"  Mensaje: {msg['text']}")
        print(f"  Chat ID: {msg['chat_id']}")
        print(f"  {'─'*50}")
    print()


def respond(msg_id: str, text: str = None, file_path: str = None):
    """Guarda respuesta y la envía."""
    if file_path:
        response = Path(file_path).read_text(encoding="utf-8")
    elif text:
        response = text
    else:
        print("Error: necesitas --text o un archivo de respuesta")
        sys.exit(1)

    save_response(msg_id, response, auto_send=True)
    print(f"Respuesta guardada para {msg_id} ({len(response)} chars)")

    # Enviar automáticamente (status='sending' evita que el bot lo duplique)
    if send_response(msg_id):
        print(f"Respuesta enviada por Telegram.")
    else:
        print(f"Error enviando. Usa 'send {msg_id}' para reintentar.")


def send(msg_id: str):
    """Envía una respuesta guardada."""
    if send_response(msg_id):
        print(f"Enviado: {msg_id}")
    else:
        print(f"Error: no se pudo enviar {msg_id}")


def send_all():
    """Envía todas las respuestas pendientes."""
    import json
    count = 0
    for f in sorted(INBOX_DIR.glob("*.json")):
        try:
            msg = json.loads(f.read_text(encoding="utf-8"))
            if msg.get("status") == "responded":
                if send_response(msg["id"]):
                    count += 1
                    print(f"  Enviado: {msg['id']}")
        except Exception as e:
            print(f"  Error con {f.name}: {e}")
    print(f"\n{count} respuestas enviadas.")


def show_failed():
    """Muestra mensajes con envío fallido."""
    failed = get_failed()
    if not failed:
        print("No hay mensajes fallidos.")
        return

    print(f"\n{'='*60}")
    print(f"  MENSAJES FALLIDOS ({len(failed)})")
    print(f"{'='*60}\n")

    for msg in failed:
        ts = msg.get("failed_at", "?")[:19].replace("T", " ")
        retries = msg.get("retry_count", 0)
        print(f"  ID: {msg['id']}")
        print(f"  De: {msg['user_name']}")
        print(f"  Último fallo: {ts}")
        print(f"  Reintentos: {retries}/3")
        print(f"  {'─'*50}")
    print()


def retry_all_failed():
    """Reintenta enviar todos los mensajes fallidos."""
    sent = retry_failed(max_retries=3)
    print(f"\n{sent} mensajes reenviados con éxito.")


def main():
    parser = argparse.ArgumentParser(description="Gestionar cola de mensajes del Investment Bot")
    parser.add_argument("action", nargs="?", default="pending",
                       choices=["pending", "respond", "send", "send-all", "failed", "retry"])
    parser.add_argument("msg_id", nargs="?", help="ID del mensaje")
    parser.add_argument("file", nargs="?", help="Archivo con la respuesta")
    parser.add_argument("--text", "-t", help="Respuesta inline")

    args = parser.parse_args()

    if args.action == "pending" or args.action is None:
        show_pending()
    elif args.action == "respond":
        if not args.msg_id:
            print("Error: falta msg_id")
            sys.exit(1)
        respond(args.msg_id, text=args.text, file_path=args.file)
    elif args.action == "send":
        if not args.msg_id:
            print("Error: falta msg_id")
            sys.exit(1)
        send(args.msg_id)
    elif args.action == "send-all":
        send_all()
    elif args.action == "failed":
        show_failed()
    elif args.action == "retry":
        retry_all_failed()


if __name__ == "__main__":
    main()
