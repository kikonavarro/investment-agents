---
name: invest-new-agent
description: >
  Crear nuevos agentes para el sistema multi-agente de inversion investment-agents.
  Usa esta skill SIEMPRE que el usuario quiera anadir un agente nuevo, crear una nueva
  capacidad del sistema, integrar un nuevo pipeline, o anadir cualquier funcionalidad
  que implique que Claude procese datos. Tambien aplica cuando el usuario diga "nuevo agente",
  "anadir agente", "crear agente", "quiero que el sistema pueda...", "anade la capacidad de...",
  o cualquier variante que implique extender el sistema con un nuevo flujo de datos.
---

# Crear un nuevo agente para investment-agents

## Principio fundamental

> Python hace el trabajo pesado (datos, calculos, filtros). Claude solo interpreta o redacta.

Esto no es una preferencia de estilo — es una decision de arquitectura con consecuencias reales.
Cada token que envias a Claude cuesta dinero y tiempo. Si Python puede calcular un ratio, no
se lo pidas a Claude. Si Python puede filtrar 3000 empresas a 15, no mandes las 3000 a Claude.

Claude entra al final del pipeline para hacer lo que Python no puede: interpretar numeros en
contexto, escribir narrativas, evaluar cualitativamente, o tomar decisiones que requieren
juicio humano.

## Arquitectura del sistema

El sistema tiene 4 capas. Cada agente nuevo debe encajar en ellas:

```
config/prompts.py    ← System prompt del agente (corto, cada token cuenta)
config/settings.py   ← Constantes, paths, modelos

agents/<nombre>.py   ← Orquesta el flujo: tool → formatter → Claude
agents/base.py       ← call_agent() y call_agent_json() — NO modificar

tools/<nombre>.py    ← Logica Python pura (datos, calculos, I/O)
tools/formatters.py  ← Compresores que reducen datos a ~150-400 tokens para Claude

main.py              ← CLI: AGENT_MAP, _call_agent(), _resolve_input(), _print_result()
agents/orchestrator.py ← Routing: prompt ORCHESTRATOR en prompts.py
```

## Proceso paso a paso

### 1. Definir el agente

Antes de escribir codigo, responde estas preguntas:

- **Que hace**: en una frase, que capacidad nueva aporta
- **Que datos necesita**: de donde vienen (yfinance, RSS, Excel, API externa, otro agente)
- **Que calcula Python**: toda la logica que NO necesita LLM
- **Que hace Claude**: interpretar, redactar, evaluar, clasificar
- **Que devuelve**: dict JSON, texto markdown, lista de strings
- **Model tier**: "quick" (Haiku — routing, formateo, clasificacion simple), "standard" (Sonnet — analisis, redaccion), "deep" (Opus — razonamiento complejo, usar poco)
- **Se encadena con otros agentes**: si/no, cuales

### 2. Crear la tool en `tools/`

Si el agente necesita datos o calculos nuevos, crea `tools/<nombre>.py`.

Reglas:
- Python puro. Sin llamadas a Claude aqui.
- Funciones simples con docstrings claros.
- Devuelve dicts o listas, nunca strings formateados para humanos.
- Maneja errores con valores por defecto, no con excepciones que maten el pipeline.

**Ejemplo** (patron real del proyecto):
```python
"""
tools/sector_analyzer.py — Analisis sectorial puro Python.
"""
import yfinance as yf

def get_sector_metrics(sector: str) -> dict:
    """Obtiene metricas agregadas de un sector."""
    # ... logica Python ...
    return {"sector": sector, "avg_pe": 18.5, "companies": [...]}
```

### 3. Crear el formatter en `tools/formatters.py`

Anade una funcion `format_<nombre>_for_llm()` que comprima los datos de la tool a un
string de ~150-400 tokens. Esto es lo que recibira Claude.

Patron de formato:
```
HEADER | contexto clave
=== SECCION ===
dato1 | dato2 | dato3
linea por item, compacto, sin redundancia
```

El formatter es critico porque determina cuanta informacion tiene Claude para trabajar
y cuantos tokens gastas por llamada. Menos es mas, pero no omitas datos que Claude
necesite para hacer su trabajo.

### 4. Crear el agente en `agents/`

El agente es una funcion que orquesta: tool → formatter → Claude.

**Patron obligatorio:**
```python
"""
agents/<nombre>.py — <descripcion corta>.
<Principio>: Python <hace X>, Claude <hace Y>.
"""
from agents.base import call_agent_json  # o call_agent para texto libre
from tools.<tool> import <funcion_datos>
from tools.formatters import format_<nombre>_for_llm
from config.prompts import <NOMBRE_PROMPT>


def run_<nombre>(<parametros>) -> dict:  # o str, o list
    """
    <Descripcion del flujo completo numerado>
    1. Python <paso 1>
    2. Python <paso 2>
    3. Claude <que interpreta/redacta>

    Args: ...
    Returns: ...
    """
    # Paso 1: Python obtiene datos
    data = <funcion_datos>(<parametros>)

    # Paso 2: Python comprime para Claude
    summary = format_<nombre>_for_llm(data)

    # Paso 3: Claude interpreta
    result = call_agent_json(
        system_prompt=<NOMBRE_PROMPT>,
        user_message=summary,
        model_tier="standard",  # o "quick" si es simple
        max_tokens=800,         # ajustar al output esperado
    )

    return result
```

**Importante:**
- Usa `call_agent_json()` si Claude debe devolver JSON estructurado.
- Usa `call_agent()` si Claude debe devolver texto libre (tesis, articulo).
- Nunca pongas el prompt inline. Siempre en `config/prompts.py`.

### 5. Escribir el prompt en `config/prompts.py`

Anade una constante `NOMBRE = """..."""` al final del archivo.

Reglas para prompts:
- **Corto**: cada token del system prompt se cobra en cada llamada al agente.
- **Rol claro**: primera frase define quien es y que recibe.
- **Output format explicito**: si es JSON, da el schema exacto con ejemplo.
- **Sin instrucciones obvias**: no digas "se claro y conciso" — desperdicias tokens.

**Ejemplo real del proyecto:**
```python
SCREENER = """Evaluador de candidatas de inversion value investing.
Recibes empresas que pasaron filtros cuantitativos. Evalua cualitativamente y rankea las mejores 5.
Considera: calidad del negocio, moat, sector, riesgos no cuantitativos.

Responde en JSON:
{
  "top_5": [
    {"ticker": "XXX", "name": "...", "rank": 1, "reason": "1-2 frases"},
    ...
  ],
  "discarded": ["XXX: razon corta en 1 frase", ...]
}"""
```

### 6. Integrar en el sistema

Hay 4 puntos de integracion en `main.py` y 1 en `agents/orchestrator.py`.

Lee `references/integration_checklist.md` para el checklist detallado de cada punto.

**Resumen rapido:**

1. **`AGENT_MAP`** en main.py — registrar la funcion
2. **`_call_agent()`** en main.py — mapear como se llama con su input
3. **`_resolve_input()`** en main.py — si se encadena con otros agentes
4. **`_print_result()`** en main.py — como se muestra en consola
5. **`ORCHESTRATOR` prompt** en prompts.py — anadir routing y ejemplo
6. **CLI args** en main.py (opcional) — si quieres un flag directo tipo `--nombre`

### 7. Verificar

Checklist final antes de dar por terminado:

- [ ] La tool funciona sin Claude (testear solo Python)
- [ ] El formatter produce output legible y compacto
- [ ] El agente devuelve el tipo correcto (dict/str/list)
- [ ] El prompt esta en prompts.py, no inline
- [ ] El model_tier es el correcto para la complejidad de la tarea
- [ ] `AGENT_MAP` tiene la nueva entrada
- [ ] `_call_agent()` sabe invocar el agente
- [ ] `_print_result()` sabe mostrar el resultado
- [ ] El `ORCHESTRATOR` prompt incluye el nuevo agente con ejemplo
- [ ] Si se encadena: `_resolve_input()` resuelve la referencia

## Errores comunes a evitar

- **Mandar datos crudos a Claude**: siempre comprimir con formatter. Un DataFrame de
  5 anos de datos puede ser 10,000 tokens. Un formatter lo reduce a 200.

- **Prompt demasiado largo**: si tu prompt tiene mas de 15 lineas, probablemente
  estas pidiendo demasiado en una sola llamada. Divide en dos agentes.

- **Usar "deep" (Opus) sin necesidad**: el 95% de las tareas van bien con "standard"
  (Sonnet). Usa "quick" (Haiku) para clasificacion, routing y formateo simple.

- **Olvidar la integracion en orchestrator**: el agente funciona con `--flag` directo
  pero no responde a lenguaje natural porque falta en el prompt del ORCHESTRATOR.

- **No manejar el caso vacio**: si la tool no encuentra datos, el agente debe devolver
  un resultado coherente (ej: `{"error": "Sin datos para X"}`), no crashear.
