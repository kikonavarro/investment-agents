"""
Telegram Bot — interfaz de Telegram para el sistema de inversión.
Hace polling cada 60s, solo acepta mensajes del usuario autorizado,
pasa el mensaje al pipeline y devuelve la respuesta por Telegram.
Funciona tanto en chat privado como en grupos.
"""
import os
import sys
import time
import io
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

POLL_INTERVAL = 60  # segundos


def _load_config():
    """Carga dotenv y devuelve token, chat_id, api_base."""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    user_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    group_id = os.environ.get("TELEGRAM_GROUP_ID", "")
    api_base = f"https://api.telegram.org/bot{token}"
    return token, user_id, group_id, api_base


def _escape_html(text: str) -> str:
    """Escapa caracteres especiales para HTML de Telegram."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _md_to_html(text: str) -> str:
    """Convierte markdown basico a HTML de Telegram."""
    import re
    # Escapar HTML primero
    text = _escape_html(text)
    # **bold** -> <b>bold</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # *italic* -> <i>italic</i> (pero no si es parte de **)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    # `code` -> <code>code</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def _format_for_telegram(text: str) -> str:
    """Convierte el output del pipeline a formato HTML limpio para Telegram."""
    import re
    lines = text.split("\n")
    result = []

    for raw_line in lines:
        stripped = raw_line.strip()

        # Saltar lineas de solo separadores (===, ---, ***)
        if re.match(r'^[=\-\*]{3,}$', stripped):
            continue

        # Lineas vacias
        if not stripped:
            if result and result[-1] != "":
                result.append("")
            continue

        # Markdown headers: ## Titulo -> negrita
        m = re.match(r'^#{1,4}\s+(.+)$', stripped)
        if m:
            result.append(f"\n<b>{_escape_html(m.group(1))}</b>")
            continue

        # Titulo del pipeline: "Valoracion de TICKER" o "VALORACION COMPLETADA:"
        if re.match(r'(Valoracion de|VALORACION COMPLETADA:)', stripped):
            result.append(f"\n{'─' * 25}")
            result.append(f"<b>{_escape_html(stripped)}</b>")
            result.append(f"{'─' * 25}")
            continue

        # Pasos: "--- PASO 1/5: ... ---"
        m = re.match(r'^-{2,}\s*(PASO \d/\d:.+?)\s*-{2,}$', stripped)
        if m:
            result.append(f"\n📋 <b>{_escape_html(m.group(1))}</b>")
            continue

        # Secciones de agente: "--- ANALYST ---"
        m = re.match(r'^-{2,}\s*([A-Z_]+)\s*-{2,}$', stripped)
        if m:
            result.append(f"\n🔹 <b>{_escape_html(m.group(1))}</b>")
            continue

        # Fechas standalone
        if re.match(r'^\d{4}-\d{2}-\d{2}', stripped):
            result.append(f"<i>{_escape_html(stripped)}</i>")
            continue

        # Escenarios: "Bear:", "Base:", "Bull:" al inicio
        m = re.match(r'^(Bear|Base|Bull|bear|base|bull):\s*(.*)$', stripped)
        if m:
            emoji = {"bear": "🐻", "base": "📊", "bull": "🐂"}.get(m.group(1).lower(), "•")
            result.append(f"  {emoji} <b>{_escape_html(m.group(1))}:</b> {_escape_html(m.group(2))}")
            continue

        # Lineas clave: valor (con indentacion en el original)
        if raw_line.startswith("    ") or raw_line.startswith("\t"):
            m = re.match(r'^([\w\s]+?):\s+(.+)$', stripped)
            if m:
                result.append(f"  <b>{_escape_html(m.group(1))}:</b> {_escape_html(m.group(2))}")
                continue

        # Archivos: "├──" y "└──"
        if "├──" in stripped or "└──" in stripped:
            result.append(f"  <code>{_escape_html(stripped)}</code>")
            continue

        # Instruccion y Plan del pipeline
        if stripped.startswith("Instruccion:") or stripped.startswith("Plan:"):
            result.append(f"<b>{_escape_html(stripped)}</b>")
            continue

        # Markdown tables: | col1 | col2 | -> formato limpio
        if stripped.startswith("|") and "|" in stripped[1:]:
            # Saltar lineas separadoras de tabla |---|---|
            if re.match(r'^\|[\s\-:|]+\|$', stripped):
                continue
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if cells:
                result.append("  " + " │ ".join(_escape_html(c) for c in cells))
            continue

        # Listas markdown: - item o * item
        m = re.match(r'^[\-\*]\s+(.+)$', stripped)
        if m:
            result.append(f"  • {_md_to_html(m.group(1))}")
            continue

        # Listas numeradas: 1. item
        m = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if m:
            result.append(f"  {m.group(1)}. {_md_to_html(m.group(2))}")
            continue

        # Resto: convertir markdown inline
        result.append(_md_to_html(stripped))

    # Limpiar lineas vacias consecutivas
    cleaned = []
    for line in result:
        if line == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def send_message(api_base: str, chat_id: str, text: str, html: bool = True):
    """Envia un mensaje por Telegram con formato HTML. Divide si supera 4096 chars."""
    url = f"{api_base}/sendMessage"

    if html:
        formatted = _format_for_telegram(text)
    else:
        formatted = text

    chunks = [formatted[i:i + 4096] for i in range(0, len(formatted), 4096)]
    for chunk in chunks:
        try:
            payload = {"chat_id": chat_id, "text": chunk}
            if html:
                payload["parse_mode"] = "HTML"
            resp = requests.post(url, json=payload)
            resp_data = resp.json()
            if not resp_data.get("ok"):
                # Log del error HTML para depurar
                print(f"[Telegram] HTML falló: {resp_data.get('description', 'unknown')}")
                # Reintentar sin formato, dividiendo el texto original
                plain_chunks = [text[i:i + 4096] for i in range(0, len(text), 4096)]
                for plain_chunk in plain_chunks:
                    requests.post(url, json={"chat_id": chat_id, "text": plain_chunk})
                return  # Ya enviamos todo en plain, no seguir con chunks HTML
        except Exception as e:
            print(f"[Telegram] Error enviando mensaje: {e}")


def get_updates(api_base: str, offset: int = 0) -> list:
    """Obtiene nuevos mensajes desde Telegram."""
    url = f"{api_base}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        resp = requests.get(url, params=params, timeout=35)
        data = resp.json()
        return data.get("result", [])
    except Exception as e:
        print(f"[Telegram] Error obteniendo updates: {e}")
        return []


# Agentes permitidos en el grupo (solo lectura, sin modificar datos)
GROUP_ALLOWED_AGENTS = {"analyst", "thesis_writer", "social_media", "news_fetcher",
                        "content_writer", "screener"}
GROUP_BLOCKED_AGENTS = {"portfolio_tracker"}

# Contexto por chat: ultimo ticker usado
_chat_context: dict[str, str] = {}


def _extract_ticker_from_steps(steps: list) -> str | None:
    """Extrae el ticker de los steps del orquestador."""
    import re
    for step in steps:
        inp = step.get("input", "")
        if isinstance(inp, str) and re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,3})?$', inp):
            return inp
    return None


def _inject_context(text: str, chat_id: str) -> str:
    """
    Inyecta el ultimo ticker solo para mensajes de seguimiento claros:
    - Mensajes muy cortos (<=4 palabras) sin nombre de empresa
    - Mensajes con pronombres de referencia explícita
    """
    import re
    words = text.strip().split()

    # Si tiene ticker explícito (mayúsculas) -> no tocar
    if re.search(r'\b[A-Z]{2,6}(\.[A-Z]{1,3})?\b', text):
        return text

    # Palabras que indican seguimiento claro
    followup_words = {"mismo", "misma", "ese", "esa", "esta", "esto", "anterior",
                      "esa", "dicha", "dicho", "ella", "el", "ahora", "tambien"}

    is_short = len(words) <= 4
    has_followup = any(w.lower() in followup_words for w in words)

    # Solo inyectar si es un seguimiento claro (corto o con pronombre)
    if is_short or has_followup:
        last_ticker = _chat_context.get(chat_id)
        if last_ticker:
            return f"{text} (ticker: {last_ticker})"

    return text


def process_message(text: str, from_group: bool = False, chat_id: str = "") -> str:
    """Pasa el mensaje por el pipeline y captura el output."""
    import json

    # Inyectar contexto si falta ticker
    enriched_text = _inject_context(text, chat_id)

    # Asegurar que el directorio del proyecto es el cwd para los imports
    project_root = str(Path(__file__).parent.parent)
    original_cwd = os.getcwd()
    os.chdir(project_root)

    try:
        from main import run_pipeline
        from agents.orchestrator import orchestrate

        # Si viene del grupo, verificar que no pida agentes bloqueados
        if from_group:
            steps = orchestrate(enriched_text)
            blocked = [s["agent"] for s in steps if s["agent"] in GROUP_BLOCKED_AGENTS]
            if blocked:
                return (f"En el grupo solo puedo hacer valoraciones, tesis, "
                        f"noticias, screener y redes sociales. "
                        f"Para cartera/portfolio, escríbeme en privado.")

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        try:
            context = run_pipeline(enriched_text)
            output = buffer.getvalue()

            # Guardar ticker del contexto para futuros mensajes
            if isinstance(context, dict) and chat_id:
                ticker = _extract_ticker_from_steps(context.get("_steps", []))
                if not ticker:
                    for key, val in context.items():
                        if isinstance(val, dict) and val.get("ticker"):
                            ticker = val["ticker"]
                            break
                if ticker:
                    _chat_context[chat_id] = ticker

            if not output.strip() and context:
                parts = []
                for key, value in context.items():
                    if key.startswith("_"):
                        continue
                    if isinstance(value, str):
                        parts.append(value)
                    elif isinstance(value, dict):
                        parts.append(json.dumps(value, indent=2, ensure_ascii=False))
                output = "\n".join(parts)

            return output.strip() if output.strip() else "Procesado, pero sin output visible."

        except Exception as e:
            return f"Error procesando: {e}"
        finally:
            sys.stdout = old_stdout

    finally:
        os.chdir(original_cwd)


def run_bot():
    """Loop principal del bot: polling cada 60 segundos."""
    token, allowed_user_id, allowed_group_id, api_base = _load_config()

    if not token:
        print("[Telegram] Error: TELEGRAM_BOT_TOKEN no configurado en .env")
        sys.exit(1)
    if not allowed_user_id:
        print("[Telegram] Error: TELEGRAM_CHAT_ID no configurado en .env")
        sys.exit(1)

    print(f"[Telegram] Bot activo. Polling cada {POLL_INTERVAL}s.")
    print(f"[Telegram] Chat privado: solo user_id {allowed_user_id}")
    if allowed_group_id:
        print(f"[Telegram] Grupo autorizado: {allowed_group_id} (todos los miembros)")
    print("[Telegram] Ctrl+C para detener.\n")

    offset = 0

    while True:
        updates = get_updates(api_base, offset)

        for update in updates:
            offset = update["update_id"] + 1

            msg = update.get("message", {})
            user_id = str(msg.get("from", {}).get("id", ""))
            chat_id = str(msg.get("chat", {}).get("id", ""))
            chat_type = msg.get("chat", {}).get("type", "private")
            text = msg.get("text", "")

            if not text or text.startswith("/"):
                continue

            # En el grupo autorizado: aceptar mensajes de cualquier miembro
            # En chat privado: solo del usuario autorizado
            is_allowed_group = allowed_group_id and chat_id == allowed_group_id
            is_allowed_private = chat_type == "private" and user_id == allowed_user_id

            if not is_allowed_group and not is_allowed_private:
                print(f"[Telegram] Mensaje ignorado de user_id: {user_id} en chat: {chat_id}")
                continue

            user_name = msg.get("from", {}).get("first_name", "Usuario")
            print(f"[Telegram] Mensaje de {user_name} ({chat_type}): {text}")

            send_message(api_base, chat_id, "⏳ Procesando tu solicitud...", html=False)

            response = process_message(text, from_group=is_allowed_group, chat_id=chat_id)

            send_message(api_base, chat_id, response)
            print(f"[Telegram] Respuesta enviada ({len(response)} chars)")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_bot()
