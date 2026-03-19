"""
Content Writer Agent — artículos para Substack en Markdown.
Input: tema + datos opcionales de soporte. Output: artículo completo.
"""
import json
from agents.base import call_agent
from config.prompts import CONTENT_WRITER
from config import settings


def run_content_writer(
    topic: str,
    supporting_data: dict = None,
) -> str:
    """
    Escribe un artículo completo para Substack.

    Args:
        topic: Tema del artículo (ej: "Por qué el tabaco sigue siendo
               una inversión value interesante en 2025")
        supporting_data: Dict opcional con datos de soporte (análisis,
                         métricas, etc.). Ya deben venir comprimidos
                         por un formatter — no pasar DataFrames crudos.

    Returns:
        Artículo en Markdown (~1500-2500 palabras)
    """
    message = f"Tema del artículo: {topic}"
    if supporting_data:
        message += f"\n\nDatos de soporte:\n{json.dumps(supporting_data, ensure_ascii=False, indent=2)}"

    # Modo data-only: devolver datos preparados sin llamar a la API
    if settings.DATA_ONLY_MODE:
        print(f"  [content_writer] Modo data-only: datos preparados para artículo")
        return message

    print(f"  [content_writer] Escribiendo artículo: '{topic[:60]}...'")
    article = call_agent(
        system_prompt=CONTENT_WRITER,
        user_message=message,
        model_tier="standard",
        max_tokens=5000,
        json_output=False,
    )
    return article
