"""Regresión del troceado HTML para Telegram.

Bug diagnosticado el 2026-05-30 (memoria project_telegram_chunking_bug) y
corregido el 2026-06-03: al partir tesis largas, <blockquote> quedaba sin
balancear (no estaba en la whitelist) y la longitud se medía con len() en vez
de en unidades UTF-16 (un emoji cuenta 2 para Telegram), por lo que algún chunk
se pasaba del límite de 4096 y el envío caía al fallback de texto plano.
"""
import re

from tools.telegram_bot import _smart_chunk, _tg_len, _strip_html, _TG_TAGS

TG_LIMIT = 4096


def _is_balanced(html: str) -> bool:
    """True si los tags soportados por Telegram están bien anidados."""
    stack = []
    for m in re.finditer(rf'<(/?)({_TG_TAGS})[^>]*>', html):
        closing, tag = m.group(1), m.group(2)
        if closing:
            if not stack or stack.pop() != tag:
                return False
        else:
            stack.append(tag)
    return not stack


def test_tg_len_counts_utf16_units():
    assert _tg_len("abc") == 3
    assert _tg_len("📈") == 2          # fuera del BMP -> 2 unidades UTF-16
    assert _tg_len("a📈b") == 4
    assert _tg_len("🐻🐂📊") == 6


def test_short_text_single_chunk():
    assert _smart_chunk("hola") == ["hola"]


def test_blockquote_split_stays_balanced():
    """El resumen ejecutivo va en <blockquote>; si es largo y se parte, cada
    chunk debe quedar con el blockquote cerrado/reabierto correctamente."""
    inner = "Línea del resumen ejecutivo con datos relevantes. " * 400
    text = f"<blockquote>{inner}</blockquote>"
    chunks = _smart_chunk(text)
    assert len(chunks) > 1
    for c in chunks:
        assert _is_balanced(c), f"chunk con HTML desbalanceado: {c[:80]!r}..."
        assert _tg_len(c) <= TG_LIMIT


def test_chunks_within_limit_with_astral_emoji():
    """Con muchos emoji astrales, medir con len() subestimaría y algún chunk
    superaría 4096 unidades UTF-16. Debe respetarse el límite real."""
    line = "📈 Bull 🐂 base 📊 bear 🐻 — números 1.234,56 → resultado\n"
    text = "".join(f"<b>{line}</b>" for _ in range(300))
    chunks = _smart_chunk(text)
    assert len(chunks) > 1
    for c in chunks:
        assert _tg_len(c) <= TG_LIMIT
        assert _is_balanced(c)


def test_nested_tags_balanced_across_split():
    inner = "<b>negrita con <i>cursiva</i> dentro</b> " * 300
    text = f"<blockquote>{inner}</blockquote>"
    chunks = _smart_chunk(text)
    assert len(chunks) > 1
    for c in chunks:
        assert _is_balanced(c)
        assert _tg_len(c) <= TG_LIMIT


def test_visible_content_preserved():
    """Los tags de frontera reintroducidos no deben alterar el texto visible."""
    inner = "Texto de prueba con <b>negrita</b> y algo más de relleno. " * 300
    text = f"<blockquote>{inner}</blockquote>"
    chunks = _smart_chunk(text)
    joined = _strip_html("".join(chunks))
    original = _strip_html(text)
    # Se ignoran espacios/saltos: el corte puede mover un \n o un espacio de borde
    assert joined.replace(" ", "").replace("\n", "") == \
        original.replace(" ", "").replace("\n", "")


def test_link_tag_not_split_midway():
    """Un <a href=...> no debe partirse a la mitad al cortar por espacios."""
    inner = " ".join(f'<a href="https://example.com/{i}">enlace {i}</a>'
                      for i in range(400))
    chunks = _smart_chunk(inner)
    assert len(chunks) > 1
    for c in chunks:
        assert _is_balanced(c)
        assert _tg_len(c) <= TG_LIMIT
