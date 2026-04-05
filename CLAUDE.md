# Investment Agents — Instrucciones para Claude Code

## Principio clave

**Python = datos. Opus = interpretación y valoración.** Python recoge datos financieros, SEC filings, noticias y métricas de referencia. Opus (Claude Code) decide WACC, TV, escenarios, calcula el DCF y escribe la tesis. Una sola fuente de verdad: la tesis.

## Sistema de skills (referencia principal)

Las 14 skills en `.claude/skills/` son la referencia operativa principal. Cada skill define qué hacer, cómo hacerlo, y los quality gates. **Leer siempre la skill antes de ejecutar.**

| Skill                  | Cuándo usarla                                                                                |
| ---------------------- | --------------------------------------------------------------------------------------------- |
| `orchestrator`       | **Entry point.** Enruta mensajes del bot y peticiones de inversión a la skill correcta |
| `thesis-writer`      | Tesis de inversión completa (incluye fórmula DCF corregida)                                 |
| `dcf-valuation`      | Referencia teórica: normalización FCF, WACC, Gordon Growth, sanity checks                   |
| `business-model`     | Modelo de negocio, unit economics, pricing power (obligatorio en toda tesis)                  |
| `moat-analyst`       | Ventaja competitiva Morningstar/Buffett (obligatorio en toda tesis)                           |
| `capital-allocation` | ROIC, dividendos, recompras, M&A (obligatorio en toda tesis)                                  |
| `risk-analyst`       | Riesgos materiales priorizados (obligatorio en toda tesis)                                    |
| `screener-ranking`   | Ranking cualitativo de las top 15 del screener cuantitativo                                   |
| `comparator`         | Comparación lado a lado de dos empresas                                                      |
| `thesis-reviewer`    | Revisar/comparar tesis externa contra la nuestra                                              |
| `ir-auditor`         | Auditar cifras del IR vs cuentas oficiales (detectar maquillaje)                              |
| `tweet-generator`    | Hilos Twitter/X sobre inversiones                                                             |
| `content-writer`     | Artículos Substack/blog                                                                      |
| `invest-new-agent`   | Guía para crear nuevos agentes/capacidades del sistema                                       |

**Nota sobre DCF:** La fórmula usa EBIT = Rev × (GM - SGA% - R&D%), EBITDA = EBIT + D&A. UFCF = EBIT×(1-T) + D&A - CapEx. Terminal Value sobre EBITDA (no EBIT). Ver `thesis-writer` Paso 1B.

## Pipeline de inversión (modo sin API)

Usar el flag `--data-only` para ejecutar solo Python y luego interpretar con Claude Code.

### Valoración completa

```bash
python main.py --analyst TICKER --data-only
python main.py --analyst AAPL MSFT GOOGL --data-only  # múltiples
```

Genera en `data/valuations/{TICKER}/`: JSON con datos crudos + métricas de referencia + Excel template + SEC filings.
Quality gates validan calidad de datos (no escenarios — eso lo decides tú al escribir la tesis).
El JSON NO contiene escenarios ni fair values. Solo datos y métricas de referencia.

### Tesis de inversión

```bash
python main.py --analyst TICKER --data-only
```

Leer JSON + SEC filings. Tú decides WACC, TV, escenarios y calculas el DCF.
Escribir tesis siguiendo skill `thesis-writer` (NO `config/prompts.py`).
Guardar en `data/valuations/{TICKER}/{TICKER}_tesis_inversion.md`.
**Guardar fair values:** `python tools/save_fair_values.py TICKER --bear X --base Y --bull Z`
**Review gate obligatorio:** `python tools/thesis_reviewer.py TICKER` antes de enviar.

### Comparar empresas

```bash
python main.py --compare TICKER1 TICKER2 --data-only
```

Genera datos de ambas. Comparar siguiendo skill `comparator`.

### Screener

```bash
python main.py --screener graham_default --data-only
```

Filtros: `graham_default`, `value_aggressive`, `bargain_hunter`. Ranking cualitativo con skill `screener-ranking`.

### Otros

```bash
python main.py --tweets TICKER          # datos para tweets
python main.py --article "topic"        # datos para artículo
python main.py --portfolio status       # cartera (usa API)
python main.py --history TICKER         # historial de valoraciones
python main.py --fresh --analyst TICKER # forzar refresh cache
```

## Estructura del JSON de valoración

El JSON (`{TICKER}_valuation.json`) contiene **solo datos crudos**:

- `latest_financials`: revenue, EBITDA, FCF, márgenes, deuda, cash
- `historical_data`: 3-5 años de métricas
- `reference_metrics`: márgenes avg, growth rates históricos, beta, EV/EBITDA, detecciones
- `sec_audit`: discrepancias Yahoo vs 10-K
- `news`: noticias recientes

**NO contiene:** `scenarios`, `dcf_reliable`, fair values, WACC ni TV auto-calculados.
Los fair values se guardan en `history.json` al escribir la tesis (`tools/save_fair_values.py`).

## AL INICIAR SESION — Acciones obligatorias

1. **Activar polling de Telegram:** Ejecutar `/loop 1m python tools/check_inbox.py` para comprobar la bandeja de entrada cada minuto. Sin esto, los mensajes del Investment Bot no se procesan.
2. Si hay mensajes pendientes, procesarlos según el tipo (tesis, screener, tweets, etc.)

**⚠️ NUNCA lanzar `telegram_bot.py` desde esta sesión.** El bot ya corre como servicio permanente via launchd (`com.investment.telegrambot`). Lanzar otra copia causa mensajes duplicados. Solo usar `check_inbox.py` para leer y responder la cola.

## Cola de mensajes Telegram (Investment Bot → Claude Code)

El Investment Bot ya NO llama a la API de Anthropic. Encola mensajes para que Claude Code (Opus) los procese:

```bash
# Ver mensajes pendientes
python tools/check_inbox.py

# Responder (guarda + envía por Telegram automáticamente)
python tools/check_inbox.py respond <msg_id> respuesta.md
python tools/check_inbox.py respond <msg_id> --text "respuesta corta"

# Enviar respuestas guardadas
python tools/check_inbox.py send-all
```

Cola en: `data/telegram_queue/inbox/` (JSON por mensaje).
El bot comprueba respuestas cada 60s y las envía automáticamente.
El scheduler encola tareas (tweets, screener) como mensajes `[SCHEDULER]`.

## Estructura de archivos clave

- `.claude/skills/` — **referencia principal** (14 skills con instrucciones detalladas)
- `config/prompts.py` — system prompts para llamadas API (legacy, skills son preferentes)
- `config/settings.py` — modelos, rutas, configuración
- `config/screener_filters.yaml` — filtros cuantitativos del screener
- `data/valuations/{TICKER}/` — output del analyst (JSON + Excel + SEC + tesis)
- `data/telegram_queue/` — cola de mensajes Investment Bot ↔ Claude Code
- `tools/check_inbox.py` — CLI para gestionar la cola
- `tools/quality_gates.py` — validación automática de cada valoración
- `tools/thesis_reviewer.py` — review gate antes de enviar tesis
- `tools/` — módulos Python puros (sin LLM)

**Nota:** Directorios parciales en `data/valuations/` (solo JSON+Excel, sin tesis) son normales — representan runs `--data-only` sin interpretación posterior.

## Tickers internacionales

- España: añadir `.MC` (ej: TEF.MC, ITX.MC, SAN.MC)
- Otros mercados europeos: consultar sufijo Yahoo Finance
- USA: ticker directo (AAPL, MSFT, etc.)
