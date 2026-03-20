"""
Risk Analyst Agent — identifica y evalúa riesgos específicos:
concentración, financiero, regulatorio, competitivo, macro, operacional, ESG.
"""
import json
from agents.base import call_agent_json
from agents.analyst import load_valuation
from config.prompts import RISK_ANALYST


def _prepare_data(valuation: dict) -> str:
    """Extrae datos relevantes para el análisis de riesgos."""
    subset = {
        "ticker": valuation.get("ticker"),
        "company": valuation.get("company"),
        "sector": valuation.get("sector"),
        "industry": valuation.get("industry"),
        "business_summary": valuation.get("business_summary", ""),
        "segments": valuation.get("segments", []),
        "historical_data": valuation.get("historical_data", {}),
        "latest_financials": valuation.get("latest_financials", {}),
        "current_price": valuation.get("current_price"),
        "scenarios": valuation.get("scenarios", {}),
    }
    return json.dumps(subset, ensure_ascii=False, indent=2)


def run_risk_analyst(analysis: dict | str) -> dict:
    """
    Identifica y evalúa los riesgos principales de una empresa.

    Args:
        analysis: dict de valoración o ticker (str) para cargar de disco.

    Returns:
        Dict con evaluación de riesgos.
    """
    if isinstance(analysis, str):
        ticker = analysis.upper()
        analysis = load_valuation(ticker)
        if analysis is None:
            raise ValueError(f"No existe valoración para {ticker}. Ejecuta --analyst primero.")

    ticker = analysis.get("ticker", "?")
    company = analysis.get("company", ticker)
    print(f"  [risk_analyst] Identificando riesgos de {ticker} (con web search)...")

    # Añadir instrucción de búsqueda al mensaje
    data = _prepare_data(analysis)
    data += (f"\n\nBusca noticias recientes sobre {company} ({ticker}) "
             f"relacionadas con riesgos regulatorios, demandas, cambios de directiva, "
             f"problemas operacionales o amenazas competitivas.")

    result = call_agent_json(
        system_prompt=RISK_ANALYST,
        user_message=data,
        model_tier="standard",
        max_tokens=2000,
        agent_name="risk_analyst",
        web_search=True,
    )
    return result
