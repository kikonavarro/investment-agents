"""
Social Media Agent — LEGACY.

Los tweets ahora los genera Claude Code vía la skill `tweet-generator`.
Este módulo mantiene run_social_media() como stub para compatibilidad.
"""


def run_social_media(content: dict, content_type: str = "analysis") -> list[str]:
    """Stub — ya no llama a la API. Usar skill tweet-generator desde Claude Code."""
    print(f"  [social_media] LEGACY: usar Claude Code + skill tweet-generator")
    return [f"[LEGACY] Usa Claude Code para generar tweets ({content_type})"]
