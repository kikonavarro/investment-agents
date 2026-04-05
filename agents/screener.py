"""
Screener Agent — busca ideas de inversión value con filtros cuantitativos.
El ranking cualitativo lo hace Claude Code vía la skill `screener-ranking`.
"""
from tools.screener_engine import run_screen


def run_screener(
    filter_name: str = "graham_default",
    markets: list[str] = None,
) -> dict:
    """
    Escanea el mercado con filtros cuantitativos y devuelve top 15.
    Claude Code hace el ranking cualitativo vía skill screener-ranking.

    Args:
        filter_name: "graham_default" | "value_aggressive" | "bargain_hunter"
        markets: ["SP500"] | ["IBEX35"] | ["SP500", "EUROSTOXX600"]
    """
    if markets is None:
        markets = ["SP500"]

    candidates = run_screen(filter_name, markets)

    if not candidates:
        return {"top_candidates": [], "total_candidates_found": 0,
                "filter_used": filter_name,
                "message": "Ninguna empresa pasó los filtros."}

    top_candidates = candidates[:15]
    print(f"  [screener] {len(top_candidates)} candidatas encontradas de {len(candidates)} escaneadas")

    return {
        "top_candidates": top_candidates,
        "total_candidates_found": len(candidates),
        "filter_used": filter_name,
    }
