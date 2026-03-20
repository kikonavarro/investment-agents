"""
Capital Allocation Agent — analiza cómo la directiva asigna capital:
ROIC vs WACC, dividendos, recompras, M&A, deuda.
"""
import json
from agents.base import call_agent_json
from agents.analyst import load_valuation
from config.prompts import CAPITAL_ALLOCATION


def _prepare_data(valuation: dict) -> str:
    """Extrae datos relevantes para el análisis de asignación de capital."""
    subset = {
        "ticker": valuation.get("ticker"),
        "company": valuation.get("company"),
        "sector": valuation.get("sector"),
        "historical_data": valuation.get("historical_data", {}),
        "latest_financials": valuation.get("latest_financials", {}),
        "current_price": valuation.get("current_price"),
        "shares_outstanding": valuation.get("shares_outstanding"),
        "scenarios": valuation.get("scenarios", {}),
    }
    return json.dumps(subset, ensure_ascii=False, indent=2)


def run_capital_allocation(analysis: dict | str) -> dict:
    """
    Analiza la asignación de capital de una empresa.

    Args:
        analysis: dict de valoración o ticker (str) para cargar de disco.

    Returns:
        Dict con evaluación de asignación de capital.
    """
    if isinstance(analysis, str):
        ticker = analysis.upper()
        analysis = load_valuation(ticker)
        if analysis is None:
            raise ValueError(f"No existe valoración para {ticker}. Ejecuta --analyst primero.")

    ticker = analysis.get("ticker", "?")
    print(f"  [capital_allocation] Analizando asignación de capital de {ticker}...")

    result = call_agent_json(
        system_prompt=CAPITAL_ALLOCATION,
        user_message=_prepare_data(analysis),
        model_tier="standard",
        max_tokens=1500,
        agent_name="capital_allocation",
    )
    return result
