"""
Orchestrator — decide qué agentes activar y en qué orden.
Usa Haiku (barato) porque solo hace routing, no análisis.
"""
import re
import json
from agents.base import call_agent_json
from config.prompts import ORCHESTRATOR


# Agentes que reciben un ticker como input y necesitan resolución
_TICKER_AGENTS = {"analyst", "thesis_writer", "news_fetcher", "social_media", "content_writer"}

# Patrón de ticker ya válido (ej: AAPL, WOSG.L, ITX.MC)
_TICKER_RE = re.compile(r'^[A-Z0-9]{1,6}(\.[A-Z]{1,3})?$')


def _resolve_step_ticker(step: dict) -> dict:
    """
    Si el input de un step parece un nombre de empresa (no un ticker válido),
    lo resuelve a ticker via Yahoo Finance search.
    """
    agent = step.get("agent", "")
    inp = step.get("input", "")

    if agent not in _TICKER_AGENTS:
        return step
    if not inp or inp in ("from_analyst", "from_news", "status", "graham_default",
                          "value_aggressive", "bargain_hunter"):
        return step
    # Si ya tiene sufijo de mercado (ej: ITX.MC, WOSG.L) -> el usuario fue explícito, no tocar
    if _TICKER_RE.match(inp) and "." in inp:
        return step

    # Sin sufijo o nombre de empresa -> siempre verificar en Yahoo Finance
    # Esto resuelve ambigüedades como ITX (¿USA o España?) -> ITX.MC
    from tools.financial_data import search_ticker
    print(f"  [orchestrator] Buscando ticker para: '{inp}'")
    results = search_ticker(inp, max_results=3)
    if results:
        resolved = results[0]["symbol"]
        name = results[0]["name"]
        if resolved != inp:
            print(f"  [orchestrator] '{inp}' -> {resolved} ({name})")
        step = {**step, "input": resolved}
    else:
        print(f"  [orchestrator] No se encontró ticker para '{inp}', usando tal cual")

    return step


def orchestrate(user_input: str) -> list[dict]:
    """
    Convierte la instrucción del usuario en un plan de ejecución.

    Returns:
        [{"agent": "analyst", "input": "AAPL"}, ...]
    """
    result = call_agent_json(
        system_prompt=ORCHESTRATOR,
        user_message=user_input,
        model_tier="quick",   # Haiku basta para routing
        max_tokens=300,
    )
    steps = result.get("steps", [])
    return [_resolve_step_ticker(s) for s in steps]
