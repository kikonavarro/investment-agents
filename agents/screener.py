"""
Screener Agent — busca ideas de inversión value.
Python escanea el mercado; Claude evalúa cualitativamente y rankea el top.
"""
from agents.base import call_agent_json
from tools.screener_engine import run_screen
from tools.formatters import format_screener_results_for_llm
from config.prompts import SCREENER
from config import settings


def run_screener(
    filter_name: str = "graham_default",
    markets: list[str] = None,
) -> dict:
    """
    1. Python escanea el universo con filtros cuantitativos
    2. Python comprime el top-15 a ~400 tokens
    3. Claude evalúa cualitativamente y rankea los mejores 5

    Args:
        filter_name: "graham_default" | "value_aggressive" | "bargain_hunter"
        markets: ["SP500"] | ["IBEX35"] | ["SP500", "EUROSTOXX600"]

    Returns:
        {"top_5": [...], "discarded": [...], "total_scanned": N}
    """
    if markets is None:
        markets = ["SP500"]

    # Python hace el trabajo pesado (puede tardar 1-3 min pero 0 tokens)
    candidates = run_screen(filter_name, markets)

    if not candidates:
        return {"top_5": [], "discarded": [], "total_scanned": 0,
                "message": "Ninguna empresa pasó los filtros."}

    # Solo las top 15 van a Claude (no las ~3000 analizadas)
    top_candidates = candidates[:15]

    # Modo data-only: devolver candidatos cuantitativos sin ranking cualitativo
    if settings.DATA_ONLY_MODE:
        print(f"  [screener] Modo data-only: {len(top_candidates)} candidatas encontradas (sin ranking cualitativo)")
        return {
            "top_candidates": top_candidates,
            "total_candidates_found": len(candidates),
            "filter_used": filter_name,
            "_data_only": True,
        }

    summary = format_screener_results_for_llm(top_candidates)

    print(f"  [screener] Enviando {len(top_candidates)} candidatas a Claude para evaluación...")
    result = call_agent_json(
        system_prompt=SCREENER,
        user_message=summary,
        model_tier="standard",
        max_tokens=800,
    )

    result["total_candidates_found"] = len(candidates)
    return result
