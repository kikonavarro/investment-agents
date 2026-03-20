"""
Moat Analyst Agent — evalúa la ventaja competitiva duradera
usando el framework Morningstar/Buffett.
"""
import json
from agents.base import call_agent_json
from agents.analyst import load_valuation
from config.prompts import MOAT_ANALYST


def _prepare_data(valuation: dict) -> str:
    """Extrae datos relevantes para el análisis de moat."""
    subset = {
        "ticker": valuation.get("ticker"),
        "company": valuation.get("company"),
        "sector": valuation.get("sector"),
        "industry": valuation.get("industry"),
        "business_summary": valuation.get("business_summary", ""),
        "segments": valuation.get("segments", []),
        "historical_data": valuation.get("historical_data", {}),
        "latest_financials": valuation.get("latest_financials", {}),
        "scenarios": valuation.get("scenarios", {}),
    }
    return json.dumps(subset, ensure_ascii=False, indent=2)


def run_moat_analyst(analysis: dict | str) -> dict:
    """
    Evalúa la ventaja competitiva de una empresa.

    Args:
        analysis: dict de valoración o ticker (str) para cargar de disco.

    Returns:
        Dict con evaluación del moat.
    """
    if isinstance(analysis, str):
        ticker = analysis.upper()
        analysis = load_valuation(ticker)
        if analysis is None:
            raise ValueError(f"No existe valoración para {ticker}. Ejecuta --analyst primero.")

    ticker = analysis.get("ticker", "?")
    company = analysis.get("company", ticker)
    print(f"  [moat_analyst] Evaluando ventaja competitiva de {ticker} (con web search)...")

    # Añadir instrucción de búsqueda al mensaje
    data = _prepare_data(analysis)
    data += (f"\n\nBusca información reciente sobre la posición competitiva de "
             f"{company} ({ticker}): cuota de mercado, nuevos competidores, "
             f"ventajas tecnológicas, patentes relevantes o cambios en el sector.")

    result = call_agent_json(
        system_prompt=MOAT_ANALYST,
        user_message=data,
        model_tier="standard",
        max_tokens=2000,
        agent_name="moat_analyst",
        web_search=True,
    )
    return result
