"""
Wrapper central para llamadas a la API de Claude.
Todos los agentes usan call_agent(). Una sola función, sin clases.

En modo DATA_ONLY_MODE, las llamadas se interceptan y no consumen API.
Esto permite usar Claude Code (suscripción Max) para la interpretación.
"""
import json
import anthropic
from config import settings
from config.settings import MODELS

client = anthropic.Anthropic()


def call_agent(
    system_prompt: str,
    user_message: str,
    model_tier: str = "standard",
    max_tokens: int = 2000,
    json_output: bool = False,
    force_api: bool = False,
) -> str:
    """
    Llamada genérica a Claude.

    Args:
        system_prompt: Instrucciones del agente (mantener corto).
        user_message: Datos/instrucción específica (solo lo necesario).
        model_tier: "quick" (Haiku), "standard" (Sonnet), "deep" (Opus).
        max_tokens: Límite de respuesta.
        json_output: Si True, fuerza respuesta JSON.
        force_api: Si True, usa la API aunque DATA_ONLY_MODE esté activo.

    Returns:
        Texto de respuesta de Claude.
    """
    if json_output:
        system_prompt += "\n\nResponde ÚNICAMENTE con JSON válido. Sin texto adicional."

    # Modo data-only: no llamar a la API (salvo force_api)
    if settings.DATA_ONLY_MODE and not force_api:
        return "[DATA_ONLY]"

    response = client.messages.create(
        model=MODELS[model_tier],
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def call_agent_json(
    system_prompt: str,
    user_message: str,
    model_tier: str = "standard",
    max_tokens: int = 2000,
    force_api: bool = False,
) -> dict:
    """Wrapper que llama a call_agent y parsea el JSON de respuesta."""
    # Modo data-only: devolver sentinel sin llamar a la API
    if settings.DATA_ONLY_MODE and not force_api:
        return {"_data_only": True}

    raw = call_agent(
        system_prompt=system_prompt,
        user_message=user_message,
        model_tier=model_tier,
        max_tokens=max_tokens,
        json_output=True,
    )
    # Limpiar posibles backticks markdown
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)
