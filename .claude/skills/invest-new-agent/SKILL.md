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
config/settings.py   ← Constantes, paths, configuración

agents/<nombre>.py   ← Orquesta el flujo Python (datos, cálculos)
                       Ya NO llaman a la API — Claude Code ejecuta vía skills

tools/<nombre>.py    ← Lógica Python pura (datos, cálculos, I/O)
tools/formatters.py  ← Formateadores de datos para output legible

.claude/skills/<nombre>/SKILL.md ← Instrucciones para Claude Code (interpretación)

main.py              ← CLI: solo comandos de datos (--analyst, --screener, --compare, etc.)
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

El agente es una función Python pura que recoge y procesa datos. Ya NO llama a la API.
La interpretación la hace Claude Code vía la skill correspondiente.

**Patrón obligatorio:**
```python
"""
agents/<nombre>.py — <descripción corta>.
Python recoge datos. Claude Code interpreta vía skill.
"""
from tools.<tool> import <funcion_datos>


def run_<nombre>(<parametros>) -> dict:
    """
    <Descripción del flujo>
    1. Python <obtiene datos>
    2. Python <procesa/formatea>
    3. Devuelve datos para que Claude Code interprete

    Args: ...
    Returns: dict con datos crudos
    """
    data = <funcion_datos>(<parametros>)
    return data
```

### 5. Crear la skill en `.claude/skills/<nombre>/SKILL.md`

La skill contiene las instrucciones para que Claude Code interprete los datos.
Ver las skills existentes como referencia (thesis-writer, screener-ranking, etc.).

```markdown
---
name: <nombre>
description: >
  <Cuándo se activa esta skill>
---

# <Nombre> — <descripción>

## Flujo
1. Ejecutar `python main.py --<comando> ARGS`
2. Leer los datos generados
3. <Instrucciones de interpretación>

## Reglas
- <Regla 1>
- <Regla 2>
```

**Ejemplo real: el screener**
- `agents/screener.py` → ejecuta filtros cuantitativos, devuelve top 15 candidatas
- `.claude/skills/screener-ranking/SKILL.md` → instrucciones para evaluar cualitativamente y rankear las 5 mejores
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
