# Test Case: Comparador de Empresas — WITH SKILL

## Files Created/Modified

1. `agents/comparator.py` (NEW) — Agente comparador
2. `tools/formatters.py` (MODIFIED) — Nuevo `format_comparison_for_llm()`
3. `config/prompts.py` (MODIFIED) — Nuevo `COMPARATOR` + actualizar `ORCHESTRATOR`
4. `main.py` (MODIFIED) — AGENT_MAP, _call_agent, _print_result, _resolve_input, CLI

---

## File: agents/comparator.py (NEW)

```python
"""
Comparator Agent — compara dos empresas lado a lado.
Flujo: Python descarga datos de ambas + DCF → Claude compara e interpreta.
"""
from agents.base import call_agent_json
from tools.dcf_calculator import extract_financials, run_full_dcf, format_dcf_report
from tools.formatters import format_comparison_for_llm
from config.prompts import COMPARATOR


def run_comparator(tickers: str | list) -> dict:
    """
    Comparacion lado a lado de dos empresas.

    1. Python extrae datos financieros de ambas (yfinance)
    2. Python ejecuta DCF completo de cada una
    3. Python comprime ambos en formato comparativo (~500 tokens)
    4. Claude compara cualitativamente y elige la mejor inversion

    Args:
        tickers: "AAPL MSFT" | "AAPL,MSFT" | ["AAPL", "MSFT"]

    Returns:
        dict con winner, confidence, comparison por dimension, resumen
    """
    # Parsear tickers
    ticker_list = _parse_tickers(tickers)
    if len(ticker_list) != 2:
        return {"error": f"Se necesitan exactamente 2 tickers, recibidos: {len(ticker_list)}"}

    t1, t2 = ticker_list

    # Paso 1: Python extrae datos de ambas
    print(f"  [comparator] Extrayendo datos de {t1}...")
    fin1 = extract_financials(t1)
    print(f"  [comparator] Extrayendo datos de {t2}...")
    fin2 = extract_financials(t2)

    # Paso 2: DCF de cada una
    print(f"  [comparator] Calculando DCF de {t1}...")
    dcf1 = run_full_dcf(fin1)
    dcf_report1 = format_dcf_report(dcf1)

    print(f"  [comparator] Calculando DCF de {t2}...")
    dcf2 = run_full_dcf(fin2)
    dcf_report2 = format_dcf_report(dcf2)

    # Paso 3: Comprimir para Claude
    print(f"  [comparator] Comprimiendo para Claude...")
    summary = format_comparison_for_llm(fin1, dcf_report1, fin2, dcf_report2)

    # Paso 4: Claude compara
    print(f"  [comparator] Claude comparando ({len(summary)} chars)...")
    result = call_agent_json(
        system_prompt=COMPARATOR,
        user_message=summary,
        model_tier="standard",
        max_tokens=1000,
    )

    # Enriquecer con datos clave
    result.setdefault("ticker_1", t1)
    result.setdefault("ticker_2", t2)
    for i, (fin, dcf) in enumerate([(fin1, dcf1), (fin2, dcf2)], 1):
        if not dcf.get("error"):
            result.setdefault(f"dcf_{i}", {
                "weighted_target": dcf["weighted_target_price"],
                "margin_of_safety_pct": dcf["margin_of_safety_pct"],
                "signal": dcf["signal"],
            })
        result.setdefault(f"price_{i}", fin.get("current_price"))

    return result


def _parse_tickers(tickers) -> list[str]:
    """Parsea tickers desde string o lista."""
    if isinstance(tickers, list):
        return [t.strip().upper() for t in tickers if t.strip()]
    if isinstance(tickers, str):
        # Soportar "AAPL MSFT", "AAPL,MSFT", "AAPL vs MSFT"
        cleaned = tickers.replace(",", " ").replace(" vs ", " ").replace(" y ", " ")
        return [t.strip().upper() for t in cleaned.split() if t.strip()]
    return []
```

---

## File: tools/formatters.py (MODIFIED — anadir al final)

```python
def format_comparison_for_llm(
    fin1: dict, dcf_report1: str,
    fin2: dict, dcf_report2: str,
) -> str:
    """
    Comprime datos de dos empresas en formato comparativo para Claude.
    Target: ~500-600 tokens.

    Output ejemplo:
        === COMPARATIVA ===
        Metrica          | AAPL              | MSFT
        Precio           | $185.50           | $420.30
        MCap             | $2,870B           | $3,120B
        Revenue          | $394B             | $236B
        ...
        === DCF: AAPL ===
        [dcf report compacto]
        === DCF: MSFT ===
        [dcf report compacto]
    """
    lines = ["=== COMPARATIVA ==="]
    lines.append(f"{'Metrica':<18s} | {fin1['ticker']:<18s} | {fin2['ticker']}")
    lines.append("-" * 60)

    # Metricas lado a lado
    metrics = [
        ("Precio", "current_price", lambda v: f"${v:,.2f}" if v else "N/A"),
        ("MCap", "market_cap", _format_large_number),
        ("Revenue", "revenue", _format_large_number),
        ("Net Income", "net_income", _format_large_number),
        ("FCF", "fcf", _format_large_number),
        ("Gross Margin", "gross_margin", lambda v: f"{v:.0%}"),
        ("Op Margin", "operating_margin", lambda v: f"{v:.0%}"),
        ("Net Margin", "net_margin", lambda v: f"{v:.0%}"),
        ("FCF Margin", "fcf_margin", lambda v: f"{v:.0%}"),
        ("ROIC", "roic", lambda v: f"{v:.0%}"),
        ("ROE", "roe", lambda v: f"{v:.0%}"),
        ("D/E", "debt_to_equity", lambda v: f"{v:.1f}" if v < 100 else "N/A"),
        ("P/E", "pe", lambda v: f"{v:.1f}" if v < 500 else "N/A"),
        ("P/B", "pb", lambda v: f"{v:.1f}" if v < 500 else "N/A"),
        ("FCF Yield", "fcf_yield", lambda v: f"{v:.1%}"),
        ("Rev CAGR 5Y", "revenue_cagr_5y", lambda v: f"{v:.1%}"),
        ("FCF CAGR 5Y", "fcf_cagr_5y", lambda v: f"{v:.1%}"),
    ]

    for label, key, fmt in metrics:
        v1 = fin1.get(key)
        v2 = fin2.get(key)
        s1 = fmt(v1) if v1 is not None else "N/A"
        s2 = fmt(v2) if v2 is not None else "N/A"
        lines.append(f"{label:<18s} | {s1:<18s} | {s2}")

    # Revenue history
    for fin in [fin1, fin2]:
        rev_hist = fin.get("revenue_history", [])
        if len(rev_hist) >= 2:
            arrow = "->".join(f"{v/1e9:.0f}" for v in rev_hist[-5:])
            lines.append(f"{fin['ticker']} Revenue ($B): {arrow}")

    # DCF reports
    lines.append(f"\n=== DCF: {fin1['ticker']} ===")
    lines.append(dcf_report1)
    lines.append(f"\n=== DCF: {fin2['ticker']} ===")
    lines.append(dcf_report2)

    return "\n".join(lines)
```

---

## File: config/prompts.py (MODIFIED)

### Nuevo prompt COMPARATOR (anadir al final):

```python
COMPARATOR = """Analista comparativo value investing. Recibes metricas y DCF de dos empresas.
Compara ambas y decide cual es mejor inversion hoy, considerando:
valoracion (margen de seguridad), calidad del negocio, crecimiento, riesgos y moat.

Responde en JSON:
{
  "winner": "TICKER",
  "confidence": "alta|media|baja",
  "comparison": [
    {"dimension": "Valoracion", "winner": "TICKER", "detail": "1 frase"},
    {"dimension": "Calidad negocio", "winner": "TICKER", "detail": "1 frase"},
    {"dimension": "Crecimiento", "winner": "TICKER", "detail": "1 frase"},
    {"dimension": "Riesgos", "winner": "TICKER", "detail": "1 frase"},
    {"dimension": "Moat", "winner": "TICKER", "detail": "1 frase"}
  ],
  "summary": "2-3 frases con la conclusion y recomendacion"
}"""
```

### Actualizar ORCHESTRATOR (anadir en lista de agentes y reglas):

Anadir a la lista de agentes disponibles:
```
analyst, news_fetcher, thesis_writer, social_media, portfolio_tracker, content_writer, screener, comparator.
```

Anadir regla de routing:
```
8. "comparator" = compara dos empresas lado a lado. Usar cuando el usuario pide comparar, enfrentar, decidir entre dos empresas, o "cual es mejor".
```

Anadir ejemplos:
```
- "Compara AAPL con MSFT" -> {"steps": [{"agent": "comparator", "input": "AAPL MSFT"}]}
- "Busca ideas value y compara las 2 mejores" -> {"steps": [{"agent": "screener", "input": "graham_default"}, {"agent": "comparator", "input": "from_screener_top2"}]}
```

---

## File: main.py (MODIFIED)

### Import (linea ~28):
```python
from agents.comparator import run_comparator
```

### AGENT_MAP (linea ~33):
```python
AGENT_MAP = {
    # ... existentes ...
    "comparator": run_comparator,
}
```

### _resolve_input (linea ~77, anadir):
```python
if agent_input == "from_screener_top2":
    top5 = context.get("screener_output", {}).get("top_5", [])
    return [t["ticker"] for t in top5[:2]]
```

### _call_agent (linea ~99, anadir elif):
```python
elif agent_name == "comparator":
    tickers = agent_input if isinstance(agent_input, (str, list)) else str(agent_input)
    return fn(tickers)
```

### _print_result (linea ~145, anadir elif):
```python
elif agent_name == "comparator":
    winner = result.get("winner", "?")
    confidence = result.get("confidence", "?")
    print(f"\n  Ganador: {winner} (confianza: {confidence})")
    for c in result.get("comparison", []):
        icon = "+" if c["winner"] == winner else "-"
        print(f"  [{icon}] {c['dimension']}: {c['winner']} — {c['detail']}")
    print(f"\n  {result.get('summary', '')}")
```

### CLI args (linea ~222, anadir):
```python
parser.add_argument("--compare", nargs=2, metavar="TICKER",
                    help="Compara dos empresas lado a lado")
```

### Handler (linea ~241, anadir):
```python
elif args.compare:
    t1, t2 = args.compare
    print(f"\n=== Comparando {t1} vs {t2} ===")
    result = run_comparator([t1, t2])
    _print_result("comparator", result)
```
