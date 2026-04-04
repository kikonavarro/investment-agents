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
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import TELEGRAM_POLL_INTERVAL as POLL_INTERVAL, TELEGRAM_MESSAGE_TIMEOUT as MESSAGE_TIMEOUT


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
    # ~~strikethrough~~ -> <s>strikethrough</s>
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    # [text](url) -> <a href="url">text</a>
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    # `code` -> <code>code</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Porcentajes con emoji: (+X%) -> 📈 (+X%), (-X%) -> 📉 (-X%)
    text = re.sub(r'\((\+\d+[\d,.]*%)\)', r'📈 (\1)', text)
    text = re.sub(r'\((-\d+[\d,.]*%)\)', r'📉 (\1)', text)
    return text


# Mapa de emoji por keyword en headers de seccion
_SECTION_EMOJI = {
    "resumen": "📋", "ejecutivo": "📋", "summary": "📋",
    "negocio": "🏢", "empresa": "🏢", "business": "🏢", "descripci": "🏢",
    "financiero": "📊", "financials": "📊", "financi": "📊",
    "valoraci": "💰", "valuation": "💰", "dcf": "💰", "precio objetivo": "💰",
    "riesgo": "⚠️", "risk": "⚠️",
    "catalizador": "🚀", "catalyst": "🚀",
    "fortaleza": "💪", "strength": "💪", "ventaja": "💪", "moat": "💪",
    "debilidad": "📉", "weakness": "📉",
    "conclusi": "✅", "veredicto": "✅", "recomendaci": "✅",
    "escenario": "🎯", "scenario": "🎯",
    "dividendo": "💵", "dividend": "💵",
    "crecimiento": "📈", "growth": "📈",
    "deuda": "🏦", "debt": "🏦", "balance": "🏦",
    "competencia": "⚔️", "competiti": "⚔️",
    "direcci": "👤", "management": "👤", "gesti": "👤",
}


def _get_section_emoji(title: str) -> str:
    """Devuelve emoji tematico segun el titulo de la seccion."""
    lower = title.lower()
    for keyword, emoji in _SECTION_EMOJI.items():
        if keyword in lower:
            return emoji
    return "▸"


def _build_header_card(text: str) -> str | None:
    """Intenta extraer ticker y metricas clave para un mini-card de cabecera."""
    import re

    # Detectar ticker del titulo (## TICKER — Nombre | ...)
    ticker_m = re.search(r'^##\s+([A-Z]{1,6}(?:\.[A-Z]{1,3})?)\s*[—–-]\s*(.+?)(?:\s*\|.*)?$',
                         text, re.MULTILINE)
    if not ticker_m:
        return None

    ticker = ticker_m.group(1)
    company = ticker_m.group(2).strip()

    # Precio actual — limpiar markdown **$13,76**
    price_m = re.search(r'precio actual de\s*\*{0,2}~?\$?([\d.,]+)', text, re.IGNORECASE)
    price = price_m.group(1) if price_m else None

    # Precio objetivo base
    target_m = re.search(r'precio objetivo base de\s*\*{0,2}~?\$?([\d.,]+)', text, re.IGNORECASE)
    if not target_m:
        target_m = re.search(r'Base\*{0,2}.*?\$?([\d.,]+)', text)
    target = target_m.group(1) if target_m else None

    # Potencial
    potential_m = re.search(r'potencial.*?(\d+[\d,.]*%)', text, re.IGNORECASE)
    potential = potential_m.group(1) if potential_m else None

    # Etiqueta de riesgo
    risk_m = re.search(r'(ESPECULATIVO|ALTO RIESGO|CONSERVADOR|MODERADO|VALUE TRAP)', text, re.IGNORECASE)
    risk_label = risk_m.group(1).upper() if risk_m else None

    # Bear/Bull rapido — buscar precio objetivo (ultimo $X en la linea, con rangos tipo $8–10)
    bear_m = re.search(r'(?:Bajista|Bear).*\~?\$([\d.,]+(?:[–\-][\d.,]+)?)', text, re.IGNORECASE)
    bull_m = re.search(r'(?:Alcista|Bull).*\~?\$([\d.,]+(?:[–\-][\d.,]+)?)', text, re.IGNORECASE)

    # Construir card
    lines = [f"━━━━━━━━━━━━━━━━━━━━━━"]
    lines.append(f"📊 <b>{_escape_html(ticker)}</b> — <i>{_escape_html(company)}</i>")

    if risk_label:
        risk_emoji = "🔴" if "ALTO" in risk_label or "ESPECUL" in risk_label else "🟡"
        lines.append(f"{risk_emoji} <b>{_escape_html(risk_label)}</b>")

    lines.append("")

    if price:
        lines.append(f"  💵 Precio actual:  <b>${_escape_html(price)}</b>")
    if target:
        upside = ""
        if potential:
            upside = f"  📈 {_escape_html(potential)}"
        lines.append(f"  🎯 Objetivo base:  <b>${_escape_html(target)}</b>{upside}")

    if bear_m or bull_m:
        range_parts = []
        if bear_m:
            range_parts.append(f"🐻 ${_escape_html(bear_m.group(1))}")
        if bull_m:
            range_parts.append(f"🐂 ${_escape_html(bull_m.group(1))}")
        lines.append(f"  {' → '.join(range_parts)}")

    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


def _format_table_block(table_lines: list[str]) -> str:
    """Convierte lineas de tabla markdown a <pre> monospace alineado."""
    import re
    rows = []
    for line in table_lines:
        # Saltar separadores |---|---|
        if re.match(r'^\|[\s\-:|]+\|$', line.strip()):
            continue
        cells = [c.strip() for c in line.strip().split("|")[1:-1]]
        # Limpiar markdown inline en celdas (**, *, ~~, `)
        cells = [re.sub(r'\*\*(.+?)\*\*', r'\1', c) for c in cells]
        cells = [re.sub(r'\*(.+?)\*', r'\1', c) for c in cells]
        cells = [re.sub(r'~~(.+?)~~', r'\1', c) for c in cells]
        cells = [re.sub(r'`(.+?)`', r'\1', c) for c in cells]
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    # Calcular ancho maximo por columna
    num_cols = max(len(r) for r in rows)
    col_widths = [0] * num_cols
    for row in rows:
        for i, cell in enumerate(row):
            if i < num_cols:
                col_widths[i] = max(col_widths[i], len(cell))

    # Formatear con padding
    formatted_rows = []
    for idx, row in enumerate(rows):
        parts = []
        for i in range(num_cols):
            cell = row[i] if i < len(row) else ""
            parts.append(cell.ljust(col_widths[i]))
        formatted_rows.append(" │ ".join(parts))
        # Separador despues del header
        if idx == 0 and len(rows) > 1:
            formatted_rows.append("─" * len(formatted_rows[0]))

    return "<pre>" + _escape_html("\n".join(formatted_rows)) + "</pre>"


def _format_for_telegram(text: str) -> str:
    """Convierte el output del pipeline a formato HTML limpio para Telegram."""
    import re

    # 1. Header card si es una tesis/valoracion
    header_card = _build_header_card(text)

    # 2. Convertir code blocks (```) antes de procesar linea a linea
    text = re.sub(
        r'```(\w*)\n(.*?)```',
        lambda m: f'<pre>{_escape_html(m.group(2).rstrip())}</pre>',
        text, flags=re.DOTALL
    )

    lines = text.split("\n")
    result = []
    in_pre = False
    table_buffer = []  # Acumular lineas de tabla consecutivas
    first_header_done = False  # Para blockquote del resumen ejecutivo
    in_summary = False  # Dentro del resumen ejecutivo
    summary_lines = []

    def _flush_table():
        """Vacia el buffer de tabla y lo formatea."""
        nonlocal table_buffer
        if table_buffer:
            result.append(_format_table_block(table_buffer))
            table_buffer = []

    def _flush_summary():
        """Vacia el resumen ejecutivo como blockquote."""
        nonlocal summary_lines, in_summary
        if summary_lines:
            content = "\n".join(summary_lines)
            result.append(f"\n<blockquote>{content}</blockquote>")
            summary_lines = []
        in_summary = False

    for raw_line in lines:
        # Dentro de <pre> no tocar nada
        if '<pre>' in raw_line:
            _flush_table()
            _flush_summary()
            in_pre = True
            result.append(raw_line)
            continue
        if '</pre>' in raw_line:
            in_pre = False
            result.append(raw_line)
            continue
        if in_pre:
            result.append(raw_line)
            continue

        stripped = raw_line.strip()

        # Acumular lineas de tabla
        if stripped.startswith("|") and "|" in stripped[1:]:
            _flush_summary()
            table_buffer.append(stripped)
            continue
        else:
            _flush_table()

        # Saltar lineas de solo separadores (===, ---, ***)
        if re.match(r'^[=\-\*]{3,}$', stripped):
            continue

        # Lineas vacias
        if not stripped:
            if in_summary:
                # Permitir una linea vacia dentro del resumen (entre header y texto)
                if summary_lines:
                    _flush_summary()
            if result and result[-1] != "":
                result.append("")
            continue

        # Markdown headers: ## Titulo -> negrita con emoji tematico
        m = re.match(r'^(#{1,4})\s+(.+)$', stripped)
        if m:
            _flush_summary()
            level = len(m.group(1))
            title = m.group(2)

            # Titulo principal (## TICKER — ...) -> ya cubierto por header_card
            if level <= 2 and re.match(r'^[A-Z]{1,6}(?:\.[A-Z]{1,3})?\s*[—–-]', title):
                if header_card:
                    continue  # Ya tenemos el card
                result.append(f"\n<b>{_escape_html(title)}</b>")
                continue

            emoji = _get_section_emoji(title)
            # Limpiar emoji/simbolos existentes del titulo
            clean_title = re.sub(r'^[⚠️🔴🟡📋📊💰🚀💪📉✅🎯]+\s*', '', title).strip()

            if level <= 2:
                # Seccion principal: separador grueso
                result.append(f"\n━━━━━━━━━━━━━━━━━━")
                result.append(f"{emoji} <b>{_escape_html(clean_title)}</b>")
            else:
                # Subseccion: sin separador
                result.append(f"\n{emoji} <b>{_escape_html(clean_title)}</b>")

            # Activar blockquote para resumen ejecutivo
            if not first_header_done and any(kw in title.lower() for kw in ["resumen", "summary", "ejecutivo"]):
                first_header_done = True
                in_summary = True

            continue

        # Si estamos dentro del resumen ejecutivo, acumular para blockquote
        if in_summary:
            summary_lines.append(_md_to_html(stripped))
            continue

        # Titulo del pipeline: "Valoracion de TICKER" o "VALORACION COMPLETADA:"
        if re.match(r'(Valoracion de|VALORACION COMPLETADA:)', stripped):
            result.append(f"\n━━━━━━━━━━━━━━━━━━")
            result.append(f"✅ <b>{_escape_html(stripped)}</b>")
            result.append(f"━━━━━━━━━━━━━━━━━━")
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

        # Escenarios: "Bear:", "Base:", "Bull:", "Bajista:", "Alcista:"
        m = re.match(r'^\*?\*?(Bear|Base|Bull|bear|base|bull|Bajista|Alcista|bajista|alcista)\*?\*?[:\s]+(.*)$', stripped)
        if m:
            label = m.group(1).lower()
            emoji_map = {"bear": "🐻", "bajista": "🐻", "base": "📊",
                         "bull": "🐂", "alcista": "🐂"}
            emoji = emoji_map.get(label, "•")
            result.append(f"  {emoji} <b>{_escape_html(m.group(1))}:</b> {_md_to_html(m.group(2))}")
            continue

        # Lineas clave: valor (con indentacion en el original)
        if raw_line.startswith("    ") or raw_line.startswith("\t"):
            m = re.match(r'^([\w\s]+?):\s+(.+)$', stripped)
            if m:
                result.append(f"  <b>{_escape_html(m.group(1))}:</b> {_md_to_html(m.group(2))}")
                continue

        # Archivos: "├──" y "└──"
        if "├──" in stripped or "└──" in stripped:
            result.append(f"  <code>{_escape_html(stripped)}</code>")
            continue

        # Instruccion y Plan del pipeline
        if stripped.startswith("Instruccion:") or stripped.startswith("Plan:"):
            result.append(f"<b>{_escape_html(stripped)}</b>")
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

    # Flush pendientes
    _flush_table()
    _flush_summary()

    # Limpiar lineas vacias consecutivas
    cleaned = []
    for line in result:
        if line == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(line)

    body = "\n".join(cleaned).strip()

    # Prepend header card si existe
    if header_card:
        body = header_card + "\n\n" + body

    return body


def _strip_html(text: str) -> str:
    """Elimina tags HTML para fallback legible (no texto crudo markdown)."""
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text


def _smart_chunk(text: str, max_len: int = 4096) -> list[str]:
    """Divide texto en chunks sin romper tags HTML ni palabras."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break

        # Buscar ultimo salto de linea dentro del limite
        cut = text.rfind("\n", 0, max_len)
        if cut <= 0:
            # Sin salto de linea, buscar ultimo espacio
            cut = text.rfind(" ", 0, max_len)
        if cut <= 0:
            cut = max_len

        chunk = text[:cut]

        # Verificar tags abiertos sin cerrar en este chunk
        import re
        open_tags = re.findall(r'<(b|i|s|u|code|pre|a)[^>]*>', chunk)
        close_tags = re.findall(r'</(b|i|s|u|code|pre|a)>', chunk)

        # Cerrar tags abiertos al final del chunk
        unclosed = list(open_tags)
        for ct in close_tags:
            if ct in unclosed:
                unclosed.remove(ct)

        for tag in reversed(unclosed):
            chunk += f"</{tag}>"

        chunks.append(chunk)

        # Reabrir tags al inicio del siguiente chunk
        remainder = text[cut:].lstrip("\n")
        for tag in unclosed:
            remainder = f"<{tag}>" + remainder

        text = remainder

    return chunks


ATTACHMENTS_DIR = Path(__file__).parent.parent / "data" / "telegram_queue" / "attachments"


def _download_telegram_file(api_base: str, file_id: str, file_name: str) -> str | None:
    """Descarga un archivo de Telegram y lo guarda en data/telegram_queue/attachments/."""
    if not file_id:
        return None
    try:
        ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
        # Obtener ruta del archivo en servidores de Telegram
        resp = requests.get(f"{api_base}/getFile", params={"file_id": file_id})
        if not resp.json().get("ok"):
            return None
        remote_path = resp.json()["result"]["file_path"]
        # Construir URL de descarga
        bot_token = api_base.split("/bot")[-1]
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{remote_path}"
        # Descargar
        file_resp = requests.get(download_url)
        if file_resp.status_code != 200:
            return None
        # Guardar con timestamp para evitar colisiones
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = file_name.replace("/", "_").replace("\\", "_")
        local_path = ATTACHMENTS_DIR / f"{ts}_{safe_name}"
        local_path.write_bytes(file_resp.content)
        return str(local_path)
    except Exception as e:
        print(f"[Telegram] Error descargando archivo: {e}")
        return None


def send_message(api_base: str, chat_id: str, text: str, html: bool = True) -> bool:
    """Envia un mensaje por Telegram con formato HTML. Divide si supera 4096 chars.
    Retorna True si todos los chunks se enviaron correctamente, False si hubo error."""
    url = f"{api_base}/sendMessage"

    if html:
        formatted = _format_for_telegram(text)
    else:
        formatted = text

    chunks = _smart_chunk(formatted) if html else [formatted[i:i + 4096] for i in range(0, len(formatted), 4096)]
    for chunk in chunks:
        try:
            payload = {"chat_id": chat_id, "text": chunk}
            if html:
                payload["parse_mode"] = "HTML"
            resp = requests.post(url, json=payload)
            resp_data = resp.json()
            if not resp_data.get("ok"):
                print(f"[Telegram] HTML falló: {resp_data.get('description', 'unknown')}")
                # Fallback: enviar version limpia (sin tags) en vez de texto crudo
                clean = _strip_html(formatted)
                plain_chunks = [clean[i:i + 4096] for i in range(0, len(clean), 4096)]
                for plain_chunk in plain_chunks:
                    fallback_resp = requests.post(url, json={"chat_id": chat_id, "text": plain_chunk})
                    if not fallback_resp.json().get("ok"):
                        return False
                return True
        except Exception as e:
            print(f"[Telegram] Error enviando mensaje: {e}")
            return False
    return True


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
                        "content_writer", "screener", "email_sender"}
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
        buffer = io.StringIO()
        sys.stdout = buffer

        try:
            context = run_pipeline(enriched_text)
            output = buffer.getvalue()
        except Exception as e:
            return f"Error procesando: {e}"
        finally:
            sys.stdout = old_stdout

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

    finally:
        os.chdir(original_cwd)


def _check_and_send_responses(api_base: str):
    """Revisa la cola por respuestas listas y las envía."""
    try:
        from tools.message_queue import get_pending, INBOX_DIR
        import json
        for f in sorted(INBOX_DIR.glob("*.json")):
            try:
                msg = json.loads(f.read_text(encoding="utf-8"))
                if msg.get("status") == "responded" and msg.get("response"):
                    send_message(api_base, msg["chat_id"], msg["response"])
                    from tools.message_queue import mark_sent
                    mark_sent(msg["id"])
                    print(f"[Telegram] Respuesta de Opus enviada a {msg['user_name']} ({len(msg['response'])} chars)")
            except Exception as e:
                print(f"[Telegram] Error enviando respuesta: {e}")
    except Exception:
        pass


def run_bot():
    """Loop principal del bot: polling + cola de mensajes para Claude Code (Opus)."""
    token, allowed_user_id, allowed_group_id, api_base = _load_config()

    if not token:
        raise RuntimeError("[Telegram] TELEGRAM_BOT_TOKEN no configurado en .env")
    if not allowed_user_id:
        raise RuntimeError("[Telegram] TELEGRAM_CHAT_ID no configurado en .env")

    print(f"[Telegram] Bot activo (modo cola → Claude Code Opus).")
    print(f"[Telegram] Polling cada {POLL_INTERVAL}s.")
    print(f"[Telegram] Chat privado: solo user_id {allowed_user_id}")
    if allowed_group_id:
        print(f"[Telegram] Grupo autorizado: {allowed_group_id} (todos los miembros)")
    print("[Telegram] Ctrl+C para detener.\n")

    # Descartar mensajes pendientes al arrancar (evitar reprocesar mensajes viejos)
    try:
        stale = get_updates(api_base, offset=0)
        if stale:
            offset = stale[-1]["update_id"] + 1
            print(f"[Telegram] Descartados {len(stale)} mensajes pendientes al arrancar.")
        else:
            offset = 0
    except Exception:
        offset = 0

    from tools.message_queue import enqueue_message

    while True:
        # 1. Recibir nuevos mensajes y encolarlos
        updates = get_updates(api_base, offset)

        for update in updates:
            offset = update["update_id"] + 1

            msg = update.get("message", {})
            user_id = str(msg.get("from", {}).get("id", ""))
            chat_id = str(msg.get("chat", {}).get("id", ""))
            chat_type = msg.get("chat", {}).get("type", "private")
            text = msg.get("text", "") or msg.get("caption", "") or ""

            # Descargar archivos adjuntos (PDF, Excel, imágenes)
            attachments = []
            document = msg.get("document")
            if document:
                file_path = _download_telegram_file(api_base, document.get("file_id"),
                                                     document.get("file_name", "document"))
                if file_path:
                    attachments.append(file_path)
                    print(f"[Telegram] Archivo descargado: {file_path}")

            # Si no hay texto ni archivos, saltar
            if not text and not attachments:
                if not msg.get("text", "").startswith("/"):
                    continue
                continue

            if text.startswith("/"):
                continue

            is_allowed_group = allowed_group_id and chat_id == allowed_group_id
            is_allowed_private = chat_type == "private" and user_id == allowed_user_id

            if not is_allowed_group and not is_allowed_private:
                print(f"[Telegram] Mensaje ignorado de user_id: {user_id} en chat: {chat_id}")
                continue

            user_name = msg.get("from", {}).get("first_name", "Usuario")
            # Incluir info de archivos en el texto del mensaje
            if attachments:
                attach_info = " ".join(f"[Archivo: {a}]" for a in attachments)
                text = f"{text} {attach_info}".strip() if text else attach_info
            print(f"[Telegram] Mensaje de {user_name} ({chat_type}): {text}")

            # Encolar para Claude Code (Opus)
            msg_id = enqueue_message(chat_id, user_name, text, from_group=is_allowed_group)
            if msg_id is None:
                print(f"[Telegram] Duplicado ignorado de {user_name}")
                continue
            send_message(api_base, chat_id,
                        "⏳ Tu mensaje está siendo analizado por Opus. Te respondo en breve.",
                        html=False)
            print(f"[Telegram] Encolado: {msg_id}")

        # 2. Enviar respuestas que Claude Code haya preparado
        _check_and_send_responses(api_base)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    import datetime
    while True:
        try:
            run_bot()
        except KeyboardInterrupt:
            print("\n[Telegram] Bot detenido.")
            break
        except BaseException as e:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[Telegram] [{ts}] Bot crashed: {type(e).__name__}: {e}. Reiniciando en 10s...",
                  flush=True)
            time.sleep(10)
