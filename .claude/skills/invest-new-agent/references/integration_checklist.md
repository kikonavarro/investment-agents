# Checklist de integracion — Donde tocar para cada agente nuevo

Este archivo detalla exactamente que anadir y donde para integrar un agente nuevo
en el sistema. Cada seccion incluye el patron exacto con placeholder `<nombre>`.

## 1. AGENT_MAP en main.py (~linea 33)

```python
from agents.<nombre> import run_<nombre>

AGENT_MAP = {
    # ... agentes existentes ...
    "<nombre>": run_<nombre>,
}
```

## 2. _call_agent() en main.py (~linea 99)

Anade un `elif` que mapee como se llama tu agente con su input.
Mira los existentes como referencia — cada agente recibe su input de forma diferente.

```python
elif agent_name == "<nombre>":
    # Adaptar segun la firma de run_<nombre>()
    param = agent_input if isinstance(agent_input, str) else "<default>"
    return fn(param)
```

**Patron segun tipo de input:**
- String simple (ticker, filtro): `fn(str(agent_input))`
- Dict de otro agente: `fn(agent_input) if isinstance(agent_input, dict) else fn({})`
- Lista de tickers: iterar como hace `analyst`

## 3. _resolve_input() en main.py (~linea 77)

Solo necesario si tu agente recibe output de otro agente (encadenamiento).
Anade un `if` para la referencia que usaras en el orchestrator.

```python
if agent_input == "from_<agente_previo>":
    return context.get("<agente_previo>_output", {})
```

**Referencias existentes:**
- `"from_analyst"` → dict completo del analyst
- `"from_screener_top3"` → lista de 3 tickers del screener
- `"from_analyst_summary"` → version comprimida del analyst para social media
- `"from_news"` → dict del news_fetcher

## 4. _print_result() en main.py (~linea 145)

Anade un `elif` para mostrar el resultado en consola de forma legible.

```python
elif agent_name == "<nombre>":
    # Adaptar segun el tipo de resultado
    if isinstance(result, dict):
        print(f"Resultado: {result.get('key_field', 'N/A')}")
    else:
        print(result)
```

## 5. ORCHESTRATOR prompt en config/prompts.py

Modificar la constante `ORCHESTRATOR` para incluir:

**En la lista de agentes disponibles (primera linea):**
```
Agentes disponibles: analyst, news_fetcher, ..., <nombre>.
```

**En las reglas de routing (anadir regla numerada):**
```
N. "<nombre>" = <descripcion de cuando usarlo>. Usar cuando el usuario pide <caso de uso>.
```

**En los ejemplos (anadir 1-2 ejemplos de routing):**
```
- "<frase del usuario>" -> {"steps": [{"agent": "<nombre>", "input": "<lo que necesita>"}]}
```

Si se encadena con otro agente:
```
- "<frase>" -> {"steps": [{"agent": "analyst", "input": "AAPL"}, {"agent": "<nombre>", "input": "from_analyst"}]}
```

## 6. CLI args en main.py (opcional)

Si quieres un flag directo (tipo `--analyst AAPL`), anade en el argparser (~linea 222):

```python
parser.add_argument("--<nombre>", metavar="PARAM",
                    help="<Descripcion corta>")
```

Y en el bloque de modo directo (~linea 241):

```python
elif args.<nombre>:
    print(f"\n=== <Nombre>: {args.<nombre>} ===")
    result = run_<nombre>(args.<nombre>)
    _print_result("<nombre>", result)
    if args.save:
        # Guardar resultado si aplica
        pass
```

## 7. Scheduler (solo si es tarea periodica)

Si el agente debe ejecutarse automaticamente, anade en `scheduler.py`:

1. Una funcion de tarea (ej: `def periodic_<nombre>():`)
2. Registrarla en `setup_schedule()` con la frecuencia deseada
3. Anadirla como opcion en `--now` del CLI del scheduler

## 8. Document generator (solo si produce reportes)

Si el agente genera contenido que debe guardarse en archivo, anade una funcion
`save_<nombre>_<formato>()` en `tools/document_generator.py`.

Formatos disponibles: markdown (.md), JSON (.json), DOCX (.docx).
Los archivos van en `data/analyses/` o `data/reports/` segun el tipo.
