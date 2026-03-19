# Blueprint v2: Sistema Multi-Agente de Inversión

# Sin frameworks — Solo Python + Claude API

# Optimizado para eficiencia de contexto

---

## Principios de Diseño

### 1. Sin frameworks de agentes

Cada agente es una función Python que llama a la API de Claude con un system prompt
específico. El orquestador es otra función que decide a quién llamar.
Nada de CrewAI, LangGraph ni dependencias innecesarias.

### 2. Eficiencia de contexto (tokens)

El contexto de Claude tiene un límite (200K tokens en Sonnet, más en Opus).
Cada token que envías cuesta dinero y ocupa espacio. Las reglas son:

- **Nunca envíes datos crudos completos** al LLM. Primero procesa con Python
  (filtra, resume, extrae lo relevante) y solo envía lo necesario.
- **Cada agente recibe SOLO lo que necesita**, no todo el historial.
- **Los agentes NO se pasan mensajes entre sí directamente**.
  Se pasan datos estructurados (JSON/dict) procesados por Python.
- **Usa el modelo adecuado para cada tarea**:
  - Haiku → tareas simples (formatear tweets, clasificar, extraer datos)
  - Sonnet → tareas de análisis y redacción (tesis, artículos, análisis)
  - Opus → solo si necesitas razonamiento muy complejo puntualmente
- **System prompts cortos y directos**. Nada de texto decorativo.
- **Respuestas estructuradas** (JSON) cuando el output va a otro agente.
  Texto libre solo cuando el output va al usuario final.

### 3. Separación clara: Python hace el trabajo pesado, Claude interpreta

```
INCORRECTO: "Claude, descarga los datos de AAPL y calcula el DCF"
            (Claude no puede descargar datos ni calcular bien)

CORRECTO:   Python descarga datos → Python calcula DCF →
            Claude recibe el resumen y lo interpreta/redacta
```

Claude es bueno analizando, interpretando, redactando y decidiendo.
Python es bueno descargando datos, calculando, filtrando y procesando.
Cada uno hace lo que mejor sabe hacer.

---

## Arquitectura

```
Usuario
  │
  ▼
main.py (CLI)
  │
  ▼
orchestrator.py ──────── Claude API (decide qué agentes activar)
  │                       Input:  instrucción del usuario (1 mensaje corto)
  │                       Output: JSON con plan de ejecución
  │
  ├──► analyst.py
  │     ├── Python: descarga datos, calcula DCF
  │     └── Claude API: interpreta resultados
  │          Input:  resumen financiero (~500-1000 tokens)
  │          Output: JSON con análisis
  │
  ├──► thesis_writer.py
  │     └── Claude API: redacta documento
  │          Input:  JSON del analyst (~1000 tokens)
  │          Output: texto largo (tesis completa)
  │
  ├──► social_media.py
  │     └── Claude API: genera tweets
  │          Input:  resumen del análisis (~300 tokens)
  │          Output: tweets formateados
  │
  ├──► portfolio_tracker.py
  │     ├── Python: lee/actualiza Excel, obtiene precios
  │     └── Claude API: genera resumen legible
  │          Input:  tabla resumen de cartera (~500 tokens)
  │          Output: texto con estado de cartera
  │
  ├──► content_writer.py
  │     └── Claude API: escribe artículo
  │          Input:  tema + datos de soporte (~1000 tokens)
  │          Output: artículo Markdown
  │
  └──► screener.py
        ├── Python: filtra universo de acciones
        └── Claude API: evalúa y rankea candidatas
             Input:  top 10-15 candidatas resumidas (~800 tokens)
             Output: JSON con ranking y comentarios
```

**Nota sobre tokens**: Cada llamada a un agente es INDEPENDIENTE.
No se acumula contexto entre agentes. Esto es clave para la eficiencia.
El orquestador pasa datos procesados (Python dicts), no conversaciones.

---

## Estructura del Proyecto

```
investment-agents/
│
├── README.md
├── requirements.txt
├── .env
├── .env.example
│
├── config/
│   ├── settings.py               # Configuración global + modelos por agente
│   ├── prompts.py                # System prompts (todos centralizados)
│   └── screener_filters.yaml    # Filtros de screening configurables
│
├── agents/
│   ├── __init__.py
│   ├── base.py                   # Clase base: gestión de llamadas a Claude API
│   ├── orchestrator.py           # Decide qué agentes activar
│   ├── analyst.py                # Análisis financiero + DCF
│   ├── thesis_writer.py          # Documento de tesis
│   ├── social_media.py           # Tweets para X
│   ├── portfolio_tracker.py      # Seguimiento de cartera (Excel)
│   ├── content_writer.py         # Artículos Substack
│   └── screener.py               # Búsqueda de ideas
│
├── tools/
│   ├── __init__.py
│   ├── financial_data.py         # Descarga datos (yfinance)
│   ├── dcf_calculator.py         # Cálculo DCF puro Python
│   ├── excel_portfolio.py        # Lee/escribe Excel de cartera
│   ├── screener_engine.py        # Filtros cuantitativos
│   ├── news_fetcher.py           # Noticias (RSS/APIs gratuitas)
│   ├── document_generator.py     # Genera DOCX/PDF
│   └── formatters.py             # Formatea datos para minimizar tokens
│
├── data/
│   ├── mi_cartera.xlsx           # TU archivo Excel de cartera
│   ├── analyses/                 # Análisis guardados
│   └── reports/                  # Documentos generados
│
├── templates/
│   ├── thesis_template.md
│   └── tweet_templates.yaml
│
└── main.py                       # Punto de entrada (CLI)
```

---

## Código Base: Gestión Eficiente de la API

### agents/base.py — La pieza central de eficiencia

```python
"""
Clase base para todos los agentes.
Gestiona las llamadas a la API de Claude de forma eficiente.
"""
import anthropic
from config.settings import MODELS

client = anthropic.Anthropic()  # Lee ANTHROPIC_API_KEY de .env

# Modelos por tipo de tarea (optimización de coste)
MODELS = {
    "quick": "claude-haiku-4-5-20251001",      # Clasificar, formatear, extraer
    "standard": "claude-sonnet-4-5-20250514",   # Análisis, redacción
    "deep": "claude-opus-4-5-20250514",         # Razonamiento complejo (usar poco)
}


def call_agent(
    system_prompt: str,
    user_message: str,
    model_tier: str = "standard",  # "quick", "standard", o "deep"
    max_tokens: int = 2000,
    json_output: bool = False,
) -> str:
    """
    Llamada genérica a Claude. Todos los agentes usan esta función.

    Args:
        system_prompt: Instrucciones del agente (mantener corto)
        user_message: Los datos/instrucción específica (solo lo necesario)
        model_tier: Nivel de modelo a usar
        max_tokens: Límite de respuesta (ajustar por tarea)
        json_output: Si True, pide respuesta en JSON

    Returns:
        Texto de respuesta de Claude
    """
    if json_output:
        system_prompt += "\n\nResponde ÚNICAMENTE con JSON válido. Sin texto adicional."

    response = client.messages.create(
        model=MODELS[model_tier],
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text
```

### tools/formatters.py — Comprime datos antes de enviarlos a Claude

```python
"""
Funciones que comprimen datos financieros para minimizar tokens.
REGLA: Nunca envíes un DataFrame completo a Claude. Envía un resumen.
"""

def format_financials_for_llm(financials: dict, ticker: str) -> str:
    """
    Toma datos financieros crudos y devuelve un resumen compacto.
    Esto es lo que se envía a Claude, NO los datos completos.

    Ejemplo de output (~400 tokens en vez de ~5000):

    AAPL | Apple Inc | Tech | USA
    Precio: $185.50 | Market Cap: $2.87T
    === ÚLTIMOS 5 AÑOS ===
    Revenue ($B): 274→294→365→383→394
    Net Income ($B): 57→63→95→100→97
    FCF ($B): 73→80→93→111→99
    Margins: Gross 43% | Op 30% | Net 25%
    ROIC: 56% | ROE: 147%
    Debt/Equity: 1.8 | Current Ratio: 0.99
    === DCF ===
    Conservador: $142 | Base: $178 | Optimista: $215
    Precio actual: $185.50
    Margen seguridad (base): -4.0%
    Señal: VALOR JUSTO
    """
    # ... implementación que extrae solo métricas clave
    pass


def format_portfolio_for_llm(portfolio_data: list[dict]) -> str:
    """
    Comprime el estado de cartera a formato mínimo para Claude.

    Ejemplo (~200 tokens):

    CARTERA | 5 posiciones | Valor total: €47,320
    Ticker  | Peso  | P&L%   | vs Target
    BATS.L  | 25%   | +12.3% | -15% (margen)
    SAN.MC  | 20%   | -3.2%  | -28% (margen)
    EUFI.PA | 20%   | +5.1%  | -8% (cerca)
    BRK-B   | 20%   | +18.7% | +2% (ALCANZADO)
    [MANUAL] Indexa RV Global | 15% | +7.2% | N/A
    """
    pass


def format_screener_results_for_llm(candidates: list[dict]) -> str:
    """
    Comprime resultados del screener a formato mínimo.

    Ejemplo (~400 tokens para 10 empresas):

    SCREENING RESULTS | Filtros Graham | 10 candidatas de 3,200 analizadas
    Ticker   | Sector     | P/E  | P/B  | D/E  | FCF Yield | ROIC
    BTI.L    | Tobacco    | 7.2  | 0.9  | 0.6  | 11.2%     | 14%
    VICI     | REIT       | 12.1 | 1.3  | 0.4  | 7.8%      | 12%
    ...
    """
    pass
```

---

## Definición de Cada Agente

### Agente 0: Orquestador

```python
# agents/orchestrator.py

from agents.base import call_agent

ORCHESTRATOR_PROMPT = """Eres un router. Dada la instrucción del usuario,
decide qué agentes activar y en qué orden.

Agentes: analyst, thesis_writer, social_media, portfolio_tracker,
content_writer, screener.

Responde SOLO JSON:
{"steps": [{"agent": "nombre", "input": "qué necesita"}]}

Ejemplos:
- "Analiza Telefónica" → {"steps": [{"agent": "analyst", "input": "TEF.MC"}]}
- "Analiza AAPL y escribe la tesis" → {"steps": [{"agent": "analyst", "input": "AAPL"}, {"agent": "thesis_writer", "input": "from_analyst"}]}
- "¿Cómo va mi cartera?" → {"steps": [{"agent": "portfolio_tracker", "input": "status"}]}
- "Busca ideas de inversión y analiza las 3 mejores" → {"steps": [{"agent": "screener", "input": "default_filters"}, {"agent": "analyst", "input": "from_screener_top3"}]}
"""

def orchestrate(user_input: str) -> list[dict]:
    """Decide el plan de ejecución."""
    response = call_agent(
        system_prompt=ORCHESTRATOR_PROMPT,
        user_message=user_input,
        model_tier="quick",        # Haiku es suficiente para routing
        max_tokens=300,            # El plan es corto
        json_output=True,
    )
    return json.loads(response)["steps"]
```

**Coste por llamada**: ~0.001$ (Haiku, ~400 tokens input + 200 output)

---

### Agente 1: Analyst Agent

```python
# agents/analyst.py

from agents.base import call_agent
from tools.financial_data import download_financials
from tools.dcf_calculator import calculate_dcf
from tools.formatters import format_financials_for_llm

ANALYST_PROMPT = """Analista financiero value investing.
Recibes un resumen de datos financieros y DCF de una empresa.
Tu trabajo: interpretar los números, identificar fortalezas/debilidades,
y dar tu evaluación.

Responde en JSON:
{
  "company": "nombre",
  "ticker": "XXX",
  "signal": "INFRAVALORADA|VALOR_JUSTO|SOBREVALORADA",
  "target_price": número,
  "margin_of_safety": porcentaje,
  "strengths": ["punto1", "punto2"],
  "weaknesses": ["punto1", "punto2"],
  "key_risks": ["riesgo1", "riesgo2"],
  "summary": "2-3 frases con la conclusión principal"
}"""

def run_analyst(ticker: str) -> dict:
    """
    1. Python descarga datos (0 tokens para Claude)
    2. Python calcula DCF (0 tokens para Claude)
    3. Python comprime a resumen (~500 tokens)
    4. Claude interpreta y analiza (~500 tokens input)
    """
    # Paso 1-2: Todo en Python, sin usar Claude
    raw_data = download_financials(ticker)
    dcf = calculate_dcf(raw_data)

    # Paso 3: Comprimir para Claude
    summary = format_financials_for_llm(raw_data, dcf, ticker)

    # Paso 4: Claude solo interpreta (contexto mínimo)
    response = call_agent(
        system_prompt=ANALYST_PROMPT,        # ~150 tokens
        user_message=summary,                # ~500 tokens
        model_tier="standard",               # Sonnet
        max_tokens=800,                      # Respuesta concisa
        json_output=True,
    )
    return json.loads(response)
```

**Coste por llamada**: ~0.01$ (Sonnet, ~700 tokens input + 800 output)

---

### Agente 2: Thesis Writer Agent

```python
# agents/thesis_writer.py

THESIS_PROMPT = """Redactor de tesis de inversión value investing.
Recibes el análisis de una empresa. Escribe la tesis completa en español.

Estructura:
1. Resumen ejecutivo (ticker, precio, target, recomendación)
2. El negocio (qué hace, moat, segmentos)
3. Análisis financiero (métricas clave, tendencias)
4. Valoración (DCF, margen de seguridad)
5. Riesgos
6. Catalizadores
7. Conclusión y plan de acción

Tono profesional pero accesible. Usa datos concretos."""

def run_thesis_writer(analysis: dict) -> str:
    """
    Recibe el JSON del analyst (ya comprimido).
    Devuelve texto largo (la tesis).
    Este es el agente que más tokens de OUTPUT usa, pero el input es pequeño.
    """
    response = call_agent(
        system_prompt=THESIS_PROMPT,
        user_message=f"Escribe la tesis para: {json.dumps(analysis, ensure_ascii=False)}",
        model_tier="standard",
        max_tokens=4000,           # La tesis es larga
        json_output=False,         # Aquí queremos texto libre
    )
    return response
```

**Coste por llamada**: ~0.05$ (Sonnet, ~1000 tokens input + 4000 output)

---

### Agente 3: Social Media Agent

```python
# agents/social_media.py

SOCIAL_PROMPT = """Creas tweets sobre inversiones en español.
Max 280 caracteres por tweet. Hilos de max 8 tweets.
Tono profesional y cercano. Incluye datos concretos.
Siempre incluye: "No es consejo de inversión".
Responde en JSON: {"tweets": ["tweet1", "tweet2", ...]}"""

def run_social_media(content: dict, content_type: str = "analysis") -> list[str]:
    """
    content_type: "analysis", "news", "portfolio_update", "idea"
    Input mínimo: solo los datos clave del análisis o noticia.
    """
    response = call_agent(
        system_prompt=SOCIAL_PROMPT,
        user_message=f"Tipo: {content_type}\nDatos: {json.dumps(content, ensure_ascii=False)}",
        model_tier="quick",        # Haiku basta para tweets
        max_tokens=1000,
        json_output=True,
    )
    return json.loads(response)["tweets"]
```

**Coste por llamada**: ~0.002$ (Haiku, ~400 tokens input + 600 output)

---

### Agente 4: Portfolio Tracker Agent (CON EXCEL)

```python
# agents/portfolio_tracker.py

from tools.excel_portfolio import read_portfolio, update_prices, add_transaction
from tools.financial_data import get_current_prices
from tools.formatters import format_portfolio_for_llm

PORTFOLIO_PROMPT = """Gestor de cartera de inversiones.
Recibes el estado actual de la cartera. Presenta un resumen claro:
- P&L de cada posición
- P&L total
- Alertas (posiciones que alcanzaron target o stop loss)
- Posiciones manuales que necesitan actualización del usuario

Sé conciso y directo. No des consejos, solo datos."""

def run_portfolio_tracker(action: str = "status", **kwargs) -> str:
    """
    Acciones:
    - "status": muestra estado actual
    - "update_prices": actualiza precios automáticos
    - "add": añade transacción (kwargs: ticker, shares, price, date)
    - "manual_update": actualiza precio de fondo manual
    """
    if action == "update_prices":
        portfolio = read_portfolio()
        # Solo actualiza las posiciones automáticas (tienen ticker)
        auto_positions = [p for p in portfolio if p["source"] == "auto"]
        tickers = [p["ticker"] for p in auto_positions]
        prices = get_current_prices(tickers)
        update_prices(prices)  # Escribe en Excel

    elif action == "manual_update":
        # Para fondos de inversión que no se pueden obtener automáticamente
        update_manual_position(
            name=kwargs["name"],
            current_value=kwargs["value"],
            date=kwargs["date"],
        )

    elif action == "add":
        add_transaction(**kwargs)

    # Leer estado actualizado y comprimir para Claude
    portfolio = read_portfolio()
    summary = format_portfolio_for_llm(portfolio)

    response = call_agent(
        system_prompt=PORTFOLIO_PROMPT,
        user_message=summary,
        model_tier="quick",        # Haiku basta para resumir una tabla
        max_tokens=800,
        json_output=False,
    )
    return response
```

---

### Excel de Cartera: Estructura

```python
# tools/excel_portfolio.py

"""
El archivo mi_cartera.xlsx tiene 3 hojas:

=== HOJA 1: "Posiciones" ===
| Ticker   | Nombre              | Tipo   | Source | Shares | Avg Price | Buy Date   | Current Price | Target | Stop Loss | Notas          |
|----------|---------------------|--------|--------|--------|-----------|------------|---------------|--------|-----------|----------------|
| BATS.L   | BAT                 | stock  | auto   | 150    | 24.50     | 2024-03-15 | 27.80         | 35.00  | 20.00     |                |
| SAN.MC   | Banco Santander     | stock  | auto   | 500    | 3.85      | 2024-06-01 | 3.72          | 5.50   | 3.00      |                |
| EUFI.PA  | Eurofins Scientific | stock  | auto   | 80     | 52.30     | 2024-09-10 | 55.00         | 72.00  | 42.00     |                |
| -        | Indexa RV Global    | fund   | manual | -      | -         | 2024-01-01 | -             | -      | -         | Actualizar 1x/mes |
| -        | MyInvestor SP500    | fund   | manual | -      | -         | 2024-02-15 | -             | -      | -         | Actualizar 1x/mes |

Columna "Source":
  - "auto"   → El sistema actualiza el precio automáticamente via yfinance
  - "manual"  → TÚ actualizas el precio/valor manualmente

Para fondos manuales, en vez de "Shares" y "Avg Price" usamos:
| Invested Amount | Current Value | Last Updated |
|-----------------|---------------|--------------|
| 10000           | 10720         | 2025-05-15   |

=== HOJA 2: "Transacciones" ===
| Fecha      | Ticker/Nombre       | Tipo   | Acción | Shares/Cantidad | Precio | Comisión | Notas |
|------------|---------------------|--------|--------|-----------------|--------|----------|-------|
| 2024-03-15 | BATS.L              | stock  | buy    | 150             | 24.50  | 4.95     |       |
| 2024-01-01 | Indexa RV Global    | fund   | buy    | 10000           | -      | 0        | Aportación inicial |
| 2025-01-01 | Indexa RV Global    | fund   | buy    | 500             | -      | 0        | Aportación mensual |

=== HOJA 3: "Watchlist" ===
| Ticker  | Nombre         | Target Buy Price | Notas                    | Añadido    |
|---------|----------------|------------------|--------------------------|------------|
| INTC    | Intel          | 22.00            | Esperar restructuring    | 2025-04-01 |
| VOW3.DE | Volkswagen     | 85.00            | Si baja por aranceles    | 2025-05-01 |
"""

import openpyxl
from pathlib import Path

PORTFOLIO_FILE = Path("data/mi_cartera.xlsx")

def read_portfolio() -> list[dict]:
    """Lee todas las posiciones del Excel."""
    wb = openpyxl.load_workbook(PORTFOLIO_FILE)
    ws = wb["Posiciones"]
    positions = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        # ... parsear cada fila a dict
        pass
    return positions

def update_prices(price_map: dict[str, float]):
    """Actualiza precios de posiciones automáticas en el Excel."""
    wb = openpyxl.load_workbook(PORTFOLIO_FILE)
    ws = wb["Posiciones"]
    for row in ws.iter_rows(min_row=2):
        ticker = row[0].value
        source = row[3].value
        if source == "auto" and ticker in price_map:
            row[8].value = price_map[ticker]  # Columna Current Price
    wb.save(PORTFOLIO_FILE)

def update_manual_position(name: str, current_value: float, date: str):
    """
    Para fondos manuales: el usuario proporciona el valor actual.
    Se actualiza en el Excel.
    """
    wb = openpyxl.load_workbook(PORTFOLIO_FILE)
    ws = wb["Posiciones"]
    for row in ws.iter_rows(min_row=2):
        if row[1].value == name and row[3].value == "manual":
            row[8].value = current_value  # Current Value
            row[9].value = date           # Last Updated
            break
    wb.save(PORTFOLIO_FILE)

def add_transaction(ticker: str, action: str, shares: float,
                    price: float, date: str, fee: float = 0):
    """Añade una transacción a la hoja de transacciones."""
    wb = openpyxl.load_workbook(PORTFOLIO_FILE)
    ws = wb["Transacciones"]
    ws.append([date, ticker, "stock", action, shares, price, fee, ""])
    wb.save(PORTFOLIO_FILE)

def get_portfolio_summary() -> dict:
    """
    Devuelve resumen calculado de la cartera.
    Todo en Python, sin usar Claude.
    """
    positions = read_portfolio()
    total_value = 0
    total_invested = 0
    summary = []

    for pos in positions:
        if pos["source"] == "auto":
            current_val = pos["shares"] * pos["current_price"]
            invested = pos["shares"] * pos["avg_price"]
            pnl_pct = (pos["current_price"] - pos["avg_price"]) / pos["avg_price"] * 100
        else:  # manual
            current_val = pos["current_value"]
            invested = pos["invested_amount"]
            pnl_pct = (current_val - invested) / invested * 100

        total_value += current_val
        total_invested += invested

        summary.append({
            "name": pos["name"],
            "source": pos["source"],
            "invested": invested,
            "current": current_val,
            "pnl_pct": round(pnl_pct, 2),
            "needs_update": pos["source"] == "manual" and pos.get("days_since_update", 0) > 30,
        })

    return {
        "total_value": total_value,
        "total_invested": total_invested,
        "total_pnl_pct": round((total_value - total_invested) / total_invested * 100, 2),
        "positions": summary,
    }
```

---

### Agente 5: Content Writer Agent

```python
# agents/content_writer.py

CONTENT_PROMPT = """Escritor de artículos de inversión para Substack. Español.
Tono profesional y conversacional. 1500-2500 palabras.
Estructura: gancho → contexto → análisis con datos → implicaciones → conclusión.
Incluye disclaimer: "Contenido educativo, no consejo de inversión."
"""

def run_content_writer(topic: str, supporting_data: dict = None) -> str:
    """
    supporting_data es opcional: puede incluir datos de otros agentes
    ya comprimidos por los formatters.
    """
    message = f"Tema: {topic}"
    if supporting_data:
        message += f"\nDatos de soporte: {json.dumps(supporting_data, ensure_ascii=False)}"

    response = call_agent(
        system_prompt=CONTENT_PROMPT,
        user_message=message,            # Mínimo necesario
        model_tier="standard",           # Sonnet para buena redacción
        max_tokens=5000,
        json_output=False,
    )
    return response
```

---

### Agente 6: Screener Agent

```python
# agents/screener.py

from tools.screener_engine import run_screen
from tools.formatters import format_screener_results_for_llm

SCREENER_PROMPT = """Evaluador de candidatas de inversión value investing.
Recibes empresas que pasaron filtros cuantitativos Graham.
Tu trabajo: evaluar cualitativamente y rankear las mejores 5.

Responde JSON:
{
  "top_5": [
    {"ticker": "XXX", "name": "...", "rank": 1, "reason": "1 frase"},
    ...
  ],
  "discarded": ["XXX: razón corta", ...]
}"""

def run_screener(filters: str = "graham_default") -> dict:
    """
    1. Python escanea el mercado (0 tokens)
    2. Python filtra cuantitativamente (0 tokens)
    3. Python comprime top 15 candidatas (~400 tokens)
    4. Claude evalúa cualitativamente y rankea (~400 tokens input)
    """
    # Todo el trabajo pesado en Python
    candidates = run_screen(filters)   # Puede tardar minutos, pero 0 tokens

    # Solo las top 15 van a Claude (no las 3000 que se escanearon)
    summary = format_screener_results_for_llm(candidates[:15])

    response = call_agent(
        system_prompt=SCREENER_PROMPT,
        user_message=summary,
        model_tier="standard",
        max_tokens=800,
        json_output=True,
    )
    return json.loads(response)
```

---

## Flujo Completo: main.py

```python
# main.py

import json
from agents.orchestrator import orchestrate
from agents.analyst import run_analyst
from agents.thesis_writer import run_thesis_writer
from agents.social_media import run_social_media
from agents.portfolio_tracker import run_portfolio_tracker
from agents.content_writer import run_content_writer
from agents.screener import run_screener

AGENT_MAP = {
    "analyst": run_analyst,
    "thesis_writer": run_thesis_writer,
    "social_media": run_social_media,
    "portfolio_tracker": run_portfolio_tracker,
    "content_writer": run_content_writer,
    "screener": run_screener,
}

def run(user_input: str):
    """Punto de entrada principal."""
    print(f"\n🎯 Instrucción: {user_input}")

    # 1. El orquestador decide el plan
    steps = orchestrate(user_input)
    print(f"📋 Plan: {json.dumps(steps, indent=2)}")

    # 2. Ejecutar cada paso, pasando outputs entre agentes
    context = {}  # Datos compartidos entre pasos

    for step in steps:
        agent_name = step["agent"]
        agent_input = step["input"]
        print(f"\n🤖 Ejecutando: {agent_name}...")

        # Resolver inputs dinámicos
        if agent_input == "from_analyst":
            agent_input = context.get("analyst_output")
        elif agent_input == "from_screener_top3":
            top3 = context.get("screener_output", {}).get("top_5", [])[:3]
            agent_input = [t["ticker"] for t in top3]

        # Ejecutar agente
        result = AGENT_MAP[agent_name](agent_input)
        context[f"{agent_name}_output"] = result

        print(f"✅ {agent_name} completado")

    return context


if __name__ == "__main__":
    while True:
        user_input = input("\n💬 ¿Qué necesitas? (q para salir): ")
        if user_input.lower() == "q":
            break
        result = run(user_input)
```

---

## Resumen de Costes Estimados por Operación

| Operación                      | Llamadas API | Modelo          | Coste aprox. |
| ------------------------------- | ------------ | --------------- | ------------ |
| "Analiza AAPL"                  | 2            | Haiku + Sonnet  | ~$0.01       |
| "Analiza y escribe tesis"       | 3            | H + S + S       | ~$0.06       |
| "¿Cómo va mi cartera?"        | 2            | H + H           | ~$0.003      |
| "Busca ideas y analiza top 3"   | 5            | H + S + 3×S    | ~$0.04       |
| "Escribe artículo sobre X"     | 2            | H + S           | ~$0.05       |
| "Haz tweet del análisis"       | 2            | H + H           | ~$0.003      |
| Pipeline completo (análisis → | 6            | H + S×3 + H×2 | ~$0.08       |
| tesis → tweet → artículo)    |              |                 |              |

Coste mensual estimado con uso moderado (5-10 análisis/semana): **$5-15/mes**

---

## Filtros de Screening por Defecto

```yaml
# config/screener_filters.yaml

graham_default:
  pe_ratio_max: 15
  pb_ratio_max: 1.5
  pe_times_pb_max: 22.5
  current_ratio_min: 1.5
  debt_to_equity_max: 0.5
  positive_earnings_years_min: 5
  market_cap_min: 500_000_000

value_aggressive:
  pe_ratio_max: 20
  pb_ratio_max: 2.0
  fcf_yield_min: 0.05
  roic_min: 0.10
  debt_to_equity_max: 1.0
  market_cap_min: 1_000_000_000

bargain_hunter:
  pe_ratio_max: 10
  pb_ratio_max: 0.8
  debt_to_equity_max: 0.3
  current_ratio_min: 2.0
  market_cap_min: 200_000_000

markets:
  us: ["SP500", "RUSSELL1000"]
  europe: ["EUROSTOXX600", "IBEX35", "DAX", "CAC40", "FTSE100"]
```

---

## Dependencias (requirements.txt)

```
# API Claude
anthropic>=0.39.0

# Datos financieros
yfinance>=0.2.40
financedatabase>=2.2.0

# Excel
openpyxl>=3.1.0

# Documentos
python-docx>=1.1.0
markdown>=3.5.0

# Utilidades
pandas>=2.2.0
numpy>=1.26.0
python-dotenv>=1.0.0
pyyaml>=6.0.0
requests>=2.31.0
rich>=13.7.0

# Publicación (opcional, instalar cuando llegues a esa fase)
# tweepy>=4.14.0
# beautifulsoup4>=4.12.0
```

---

## Plan de Construcción

### Fase 1 (Semana 1-2): Herramientas Python

- Estructura de carpetas
- `tools/financial_data.py` — descarga datos con yfinance
- `tools/dcf_calculator.py` — cálculo DCF puro Python
- `tools/excel_portfolio.py` — CRUD del Excel de cartera
- `tools/formatters.py` — compresores de datos
- `agents/base.py` — función call_agent
- Tests

### Fase 2 (Semana 3-4): Agentes individuales

- Analyst Agent + Screener Agent (los más útiles primero)
- Portfolio Tracker Agent
- Thesis Writer Agent
- Social Media + Content Writer

### Fase 3 (Semana 5-6): Orquestador + integración

- Orchestrator que conecta todo
- main.py con CLI interactivo
- Flujos end-to-end testeados

### Fase 4 (Semana 7-8): Automatización

- Scheduling (screener semanal, portfolio diario)
- Generación de Excel de cartera bonito con formatos
- Alertas (precio objetivo alcanzado)
- Publicación en X y Substack (opcional)

---

## Prompt para Claude Code (copia y pega para empezar)

```
Quiero construir un sistema multi-agente de inversión en Python puro con la API
de Claude (sin CrewAI ni frameworks). Cada agente es una función que llama a la
API con un system prompt específico.

PRINCIPIO CLAVE: Python hace el trabajo pesado (descargar datos, calcular,
filtrar). Claude solo interpreta y redacta. Minimizar tokens en cada llamada.

Empecemos con la Fase 1:

1. Crea la estructura de carpetas según el blueprint
2. Crea requirements.txt, .env.example, y config/settings.py
3. Implementa agents/base.py con la función call_agent (wrapper de la API)
4. Implementa tools/financial_data.py:
   - download_financials(ticker) → descarga income statement, balance sheet,
     cash flow de los últimos 10 años con yfinance
   - get_current_prices(tickers) → precios actuales de una lista de tickers
5. Implementa tools/dcf_calculator.py:
   - calculate_dcf(financials) → 3 escenarios (conservador, base, optimista)
   - Usa FCF histórico, growth rate estimado, WACC 10% por defecto,
     terminal growth 2.5%
6. Implementa tools/formatters.py:
   - format_financials_for_llm() → comprime datos a ~500 tokens max

Vamos paso a paso. Empieza por la estructura y base.py.
```
