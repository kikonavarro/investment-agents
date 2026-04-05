"""
Content Writer — LEGACY.

Los artículos ahora los escribe Claude Code vía la skill `content-writer`.
Este módulo mantiene run_content_writer() como stub para compatibilidad.
"""


def run_content_writer(topic: str, supporting_data: dict = None) -> str:
    """Stub — ya no llama a la API. Usar skill content-writer desde Claude Code."""
    print(f"  [content_writer] LEGACY: usar Claude Code + skill content-writer")
    return f"[LEGACY] Usa Claude Code para escribir artículo sobre: {topic}"
