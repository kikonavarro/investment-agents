"""
Business Model Agent — analiza fuentes de ingresos, unit economics,
escalabilidad y dependencias del modelo de negocio.
"""
import json
from agents.base import call_agent_json
from agents.analyst import load_valuation
from config.prompts import BUSINESS_MODEL


def _prepare_data(valuation: dict) -> str:
    """Extrae datos relevantes para el análisis de modelo de negocio."""
    subset = {
        "ticker": valuation.get("ticker"),
        "company": valuation.get("company"),
        "sector": valuation.get("sector"),
        "industry": valuation.get("industry"),
        "business_summary": valuation.get("business_summary", ""),
        "segments": valuation.get("segments", []),
        "historical_data": valuation.get("historical_data", {}),
        "latest_financials": valuation.get("latest_financials", {}),
    }
    return json.dumps(subset, ensure_ascii=False, indent=2)


def run_business_model(analysis: dict | str) -> dict:
    """
    Analiza el modelo de negocio de una empresa.

    Args:
        analysis: dict de valoración o ticker (str) para cargar de disco.

    Returns:
        Dict con evaluación del modelo de negocio.
    """
    if isinstance(analysis, str):
        ticker = analysis.upper()
        analysis = load_valuation(ticker)
        if analysis is None:
            raise ValueError(f"No existe valoración para {ticker}. Ejecuta --analyst primero.")

    ticker = analysis.get("ticker", "?")
    print(f"  [business_model] Analizando modelo de negocio de {ticker}...")

    result = call_agent_json(
        system_prompt=BUSINESS_MODEL,
        user_message=_prepare_data(analysis),
        model_tier="standard",
        max_tokens=1500,
        agent_name="business_model",
    )
    return result
