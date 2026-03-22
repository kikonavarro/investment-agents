"""
Email Sender — envío de tesis de inversión por email con adjuntos.
Usa Gmail SMTP con app password. Si no está configurado, falla silenciosamente.
"""
import os
import re
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import date

log = logging.getLogger(__name__)

_config = None

MAX_ATTACHMENT_MB = 25


def _get_config():
    """Carga config SMTP (lazy, una sola vez)."""
    global _config
    if _config is not None:
        return _config

    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    default_to = os.environ.get("EMAIL_DEFAULT_TO", "")

    _config = {
        "user": user,
        "password": password,
        "default_to": default_to,
        "enabled": bool(user and password),
    }
    return _config


def is_enabled() -> bool:
    """True si SMTP está configurado."""
    return _get_config()["enabled"]


def _thesis_to_html(md_text: str) -> str:
    """Convierte markdown de tesis a HTML con estilos inline para email."""
    lines = md_text.split("\n")
    html_lines = []

    for line in lines:
        stripped = line.strip()

        # Separadores
        if re.match(r'^-{3,}$', stripped) or re.match(r'^\*{3,}$', stripped):
            html_lines.append('<hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">')
            continue

        # Headers
        m = re.match(r'^(#{1,4})\s+(.+)$', stripped)
        if m:
            level = len(m.group(1))
            title = _md_inline(m.group(2))
            styles = {
                1: "color:#1F4E79;font-size:22px;font-weight:bold;margin:24px 0 12px;border-bottom:2px solid #1F4E79;padding-bottom:6px;",
                2: "color:#1F4E79;font-size:18px;font-weight:bold;margin:20px 0 10px;border-bottom:1px solid #2E74B5;padding-bottom:4px;",
                3: "color:#2E74B5;font-size:15px;font-weight:bold;margin:16px 0 8px;",
                4: "color:#2E74B5;font-size:14px;font-weight:bold;margin:12px 0 6px;",
            }
            style = styles.get(level, styles[4])
            html_lines.append(f'<div style="{style}">{title}</div>')
            continue

        # Tablas: acumular filas
        if stripped.startswith("|") and "|" in stripped[1:]:
            # Separador de tabla (|---|---|)
            if re.match(r'^\|[\s\-:|]+\|$', stripped):
                continue
            cells = [_md_inline(c.strip()) for c in stripped.split("|")[1:-1]]
            is_header = not html_lines or not html_lines[-1].strip().startswith("<tr")
            if is_header and not any("<table" in l for l in html_lines[-5:] if l):
                html_lines.append('<table style="border-collapse:collapse;width:100%;margin:12px 0;font-size:13px;">')
            tag = "th" if is_header and not any("<th" in l for l in html_lines[-3:] if l) else "td"
            cell_style = 'style="border:1px solid #ddd;padding:6px 10px;text-align:left;"'
            header_style = 'style="border:1px solid #ddd;padding:6px 10px;text-align:left;background:#1F4E79;color:white;font-weight:bold;"'
            style = header_style if tag == "th" else cell_style
            row = "<tr>" + "".join(f"<{tag} {style}>{c}</{tag}>" for c in cells) + "</tr>"
            html_lines.append(row)
            continue

        # Cerrar tabla si la línea anterior era tabla y esta no
        if html_lines and "<tr" in (html_lines[-1] if html_lines else ""):
            if not stripped.startswith("|"):
                html_lines.append("</table>")

        # Línea vacía
        if not stripped:
            html_lines.append("<br>")
            continue

        # Listas
        m = re.match(r'^[\-\*]\s+(.+)$', stripped)
        if m:
            html_lines.append(f'<div style="margin:2px 0 2px 20px;">• {_md_inline(m.group(1))}</div>')
            continue
        m = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if m:
            html_lines.append(f'<div style="margin:2px 0 2px 20px;">{m.group(1)}. {_md_inline(m.group(2))}</div>')
            continue

        # Párrafo normal
        html_lines.append(f'<p style="margin:6px 0;line-height:1.5;">{_md_inline(stripped)}</p>')

    # Cerrar tabla pendiente
    if html_lines and "<tr" in html_lines[-1]:
        html_lines.append("</table>")

    body = "\n".join(html_lines)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;">
<div style="max-width:700px;margin:20px auto;background:white;padding:30px 40px;font-family:'Segoe UI',Arial,sans-serif;font-size:14px;color:#333;border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
{body}
<div style="margin-top:30px;padding-top:15px;border-top:1px solid #ddd;font-size:11px;color:#999;text-align:center;">
Enviado por Investment Agents · {date.today().strftime('%d/%m/%Y')}
</div>
</div>
</body>
</html>"""


def _md_inline(text: str) -> str:
    """Convierte markdown inline (**bold**, *italic*, `code`) a HTML."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code style="background:#f0f0f0;padding:1px 4px;border-radius:3px;font-size:12px;">\1</code>', text)
    return text


def _collect_attachments(ticker: str) -> list[Path]:
    """Encuentra archivos adjuntables para un ticker."""
    from config.settings import VALUATIONS_DIR
    from agents.analyst import _clean_ticker

    clean = _clean_ticker(ticker)
    folder = VALUATIONS_DIR / clean
    if not folder.exists():
        return []

    files = []

    # Tesis DOCX
    docx = folder / f"{clean}_tesis_inversion.docx"
    if docx.exists():
        files.append(docx)

    # Excel DCF
    xlsx = folder / f"{clean}_modelo_valoracion.xlsx"
    if xlsx.exists():
        files.append(xlsx)

    # SEC filings
    sec_dir = folder / "SEC_filings"
    if sec_dir.exists():
        for f in sorted(sec_dir.glob("*.htm")):
            files.append(f)

    # Verificar tamaño total
    total_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
    if total_mb > MAX_ATTACHMENT_MB:
        log.warning(f"[email] Adjuntos demasiado grandes ({total_mb:.1f}MB). Omitiendo SEC filings.")
        files = [f for f in files if "SEC_filings" not in str(f)]

    return files


def send_thesis_email(
    ticker: str,
    recipient: str | None = None,
    thesis_md: str | None = None,
) -> dict:
    """
    Envía tesis de inversión por email con adjuntos.

    Args:
        ticker: Ticker de la empresa.
        recipient: Email destino. Si None, usa EMAIL_DEFAULT_TO.
        thesis_md: Texto markdown de la tesis. Si None, lee del disco.

    Returns:
        {"success": bool, "message": str, "recipient": str}
    """
    cfg = _get_config()

    if not cfg["enabled"]:
        msg = "SMTP no configurado. Añade SMTP_USER y SMTP_PASSWORD a .env"
        log.warning(f"[email] {msg}")
        print(f"  [!] {msg}")
        return {"success": False, "message": msg, "recipient": ""}

    # Resolver destinatario
    to = recipient or cfg["default_to"]
    if not to:
        msg = "No se indicó email destinatario ni hay EMAIL_DEFAULT_TO en .env"
        print(f"  [!] {msg}")
        return {"success": False, "message": msg, "recipient": ""}

    # Cargar tesis si no viene por parámetro
    if not thesis_md:
        from config.settings import VALUATIONS_DIR
        from agents.analyst import _clean_ticker
        clean = _clean_ticker(ticker)
        md_path = VALUATIONS_DIR / clean / f"{clean}_tesis_inversion.md"
        if md_path.exists():
            thesis_md = md_path.read_text(encoding="utf-8")
        else:
            msg = f"No se encontró tesis para {ticker} en {md_path}"
            print(f"  [!] {msg}")
            return {"success": False, "message": msg, "recipient": to}

    # Extraer nombre de empresa del markdown
    company_match = re.search(r'^##\s+\S+\s*[—–-]\s*(.+?)(?:\s*\|.*)?$', thesis_md, re.MULTILINE)
    company = company_match.group(1).strip() if company_match else ticker

    # Construir email
    msg = MIMEMultipart()
    msg["From"] = cfg["user"]
    msg["To"] = to
    msg["Subject"] = f"Tesis de Inversión: {ticker} — {company} ({date.today().strftime('%d/%m/%Y')})"

    # Body HTML
    html_body = _thesis_to_html(thesis_md)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Adjuntos
    attachments = _collect_attachments(ticker)
    attached_names = []
    for filepath in attachments:
        try:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(filepath.read_bytes())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={filepath.name}")
            msg.attach(part)
            attached_names.append(filepath.name)
        except Exception as e:
            log.warning(f"[email] Error adjuntando {filepath.name}: {e}")

    # Enviar
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)

        adjuntos_str = ", ".join(attached_names) if attached_names else "sin adjuntos"
        result_msg = f"Email enviado a {to} ({len(attached_names)} adjuntos: {adjuntos_str})"
        print(f"  ✉ {result_msg}")
        log.info(f"[email] {result_msg}")
        return {"success": True, "message": result_msg, "recipient": to}

    except smtplib.SMTPAuthenticationError:
        msg = "Error de autenticación SMTP. Verifica SMTP_USER y SMTP_PASSWORD (app password de Gmail)"
        print(f"  [!] {msg}")
        log.error(f"[email] {msg}")
        return {"success": False, "message": msg, "recipient": to}
    except Exception as e:
        msg = f"Error enviando email: {e}"
        print(f"  [!] {msg}")
        log.error(f"[email] {msg}")
        return {"success": False, "message": msg, "recipient": to}
