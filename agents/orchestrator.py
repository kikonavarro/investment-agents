"""
Orchestrator — LEGACY.

El routing ahora lo hace la skill `orchestrator` de Claude Code.
Este módulo mantiene _resolve_step_ticker() como utilidad
y orchestrate() como stub para compatibilidad con telegram_bot.py.
"""
import re
from tools.financial_data import search_ticker

_TICKER_RE = re.compile(r'^[A-Z0-9]{1,6}(\.[A-Z]{1,3})?$')


def resolve_ticker(query: str) -> str | None:
    """Resuelve un nombre de empresa o ticker ambiguo a su ticker Yahoo Finance."""
    if _TICKER_RE.match(query) and "." in query:
        return query  # Ya tiene sufijo explícito
    results = search_ticker(query, max_results=3)
    if results:
        return results[0]["symbol"]
    return None


def orchestrate(user_input: str) -> list[dict]:
    """Stub — ya no llama a la API. El routing lo hace Claude Code vía skills."""
    print("  [orchestrator] LEGACY: usar Claude Code + skills en vez de orchestrate()")
    return [{"agent": "analyst", "input": user_input}]
