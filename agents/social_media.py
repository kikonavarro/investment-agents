"""
Social Media Agent — genera hilos de Twitter/X sobre análisis de inversión.
Input: dict del analyst (ya comprimido). Output: lista de tweets.
"""
import json
from agents.base import call_agent_json
from config.prompts import SOCIAL_MEDIA
from config import settings


def run_social_media(
    content: dict,
    content_type: str = "analysis",
) -> list[str]:
    """
    Genera un hilo de tweets a partir de un análisis o dato financiero.

    Args:
        content: dict del analyst, o cualquier dict con datos relevantes
        content_type: "analysis" | "portfolio_update" | "idea" | "news"

    Returns:
        Lista de strings, cada uno ≤280 caracteres
    """
    message = f"Tipo de contenido: {content_type}\n{json.dumps(content, ensure_ascii=False)}"

    # Modo data-only: devolver datos preparados sin llamar a la API
    if settings.DATA_ONLY_MODE:
        print(f"  [social_media] Modo data-only: datos preparados (tipo: {content_type})")
        return [f"[DATA_ONLY] Datos preparados para generar tweets ({content_type})"]

    print(f"  [social_media] Generando hilo de tweets (tipo: {content_type})...")
    result = call_agent_json(
        system_prompt=SOCIAL_MEDIA,
        user_message=message,
        model_tier="quick",   # Haiku basta para tweets
        max_tokens=1200,
    )

    tweets = result.get("tweets", [])

    # Validar longitud (truncar si alguno se pasa)
    tweets = [t[:280] for t in tweets if t.strip()]
    return tweets
