# Progreso del Sistema Multi-Agente de Inversión

## Estado general

| Fase | Descripción | Estado |
|------|-------------|--------|
| Fase 1 | Herramientas Python (datos, DCF, formatters) | ✅ Completada |
| Fase 2 | Agentes individuales | ✅ Completada |
| Fase 3 | Orquestador + CLI | ✅ Completada |
| Fase 4 | Automatización, scheduling, alertas | ⏳ Pendiente |

---

## Fase 1 — Herramientas Python

### Archivos creados

| Archivo | Qué hace |
|---------|----------|
| `config/settings.py` | Configuración global: modelos por tier, defaults DCF (WACC vía CAPM, exit multiple), paths |
| `config/screener_filters.yaml` | Filtros configurables: `graham_default`, `value_aggressive`, `bargain_hunter` |
| `.env.example` | Plantilla de variables de entorno |
| `requirements.txt` | Dependencias del proyecto |
| `agents/base.py` | `call_agent()` y `call_agent_json()` — wrapper central de la API de Claude |
| `tools/financial_data.py` | `download_financials(ticker)` y `get_current_prices(tickers)` vía yfinance |
| `tools/dcf_calculator.py` | DCF Revenue × Margins → UFCF. 3 escenarios, exit multiple por sector, WACC vía CAPM, sensibilidad, sanity checks |
| `tools/formatters.py` | `format_financials_for_llm()`, `format_portfolio_for_llm()`, `format_screener_results_for_llm()` |

### Validaciones

- Descarga de datos de AAPL: ✅ 4 años de revenue, FCF, net income
- DCF calculado correctamente: ✅ 3 escenarios con señal automática
- Formato comprimido: ✅ ~150 tokens (objetivo era 500)
- Dividendo corregido: yfinance devuelve `dividendYield` escalado — normalizado en `formatters.py`

---

## Fase 2 — Agentes individuales

### Archivos creados

| Archivo | Qué hace | Modelo |
|---------|----------|--------|
| `config/prompts.py` | Todos los system prompts centralizados | — |
| `agents/analyst.py` | Descarga datos → calcula DCF → Claude interpreta | Sonnet |
| `agents/thesis_writer.py` | Recibe JSON del analyst → redacta tesis completa en Markdown | Sonnet |
| `agents/social_media.py` | Hilo de tweets desde un análisis | Haiku |
| `agents/portfolio_tracker.py` | Gestiona Excel de cartera → Claude genera resumen | Haiku |
| `agents/content_writer.py` | Artículo para Substack dado un tema + datos de soporte | Sonnet |
| `agents/screener.py` | Escanea universo → Claude rankea top 5 cualitativamente | Sonnet |
| `tools/excel_portfolio.py` | CRUD completo de `mi_cartera.xlsx` (stocks auto + fondos manuales) |  — |
| `tools/screener_engine.py` | Filtros cuantitativos Graham/value sobre universo de acciones | — |

### Estructura de `mi_cartera.xlsx`

Tres hojas:
- **Posiciones** — stocks (`source=auto`, precio actualizable vía yfinance) y fondos (`source=manual`, precio manual)
- **Transacciones** — historial de compras/ventas
- **Watchlist** — empresas en seguimiento con precio objetivo de entrada

### Costes estimados por agente

| Agente | Modelo | Input | Output | Coste aprox. |
|--------|--------|-------|--------|-------------|
| Analyst | Sonnet | ~150 tokens | ~800 tokens | ~$0.008 |
| Thesis Writer | Sonnet | ~1000 tokens | ~4000 tokens | ~$0.05 |
| Social Media | Haiku | ~400 tokens | ~800 tokens | ~$0.001 |
| Portfolio Tracker | Haiku | ~200 tokens | ~600 tokens | ~$0.001 |
| Content Writer | Sonnet | ~1000 tokens | ~5000 tokens | ~$0.06 |
| Screener | Sonnet | ~400 tokens | ~600 tokens | ~$0.005 |
| Orchestrator | Haiku | ~200 tokens | ~200 tokens | ~$0.0005 |

---

## Fase 3 — Orquestador + CLI

### Archivos creados

| Archivo | Qué hace |
|---------|----------|
| `agents/orchestrator.py` | Convierte lenguaje natural en plan de ejecución JSON (Haiku) |
| `main.py` | CLI completo con modo interactivo, comandos directos y lenguaje natural |

### Comandos disponibles

```bash
# Lenguaje natural (pasa por el orquestador)
python main.py "Analiza AAPL"
python main.py "Analiza AAPL y escribe la tesis"
python main.py "¿Cómo va mi cartera?"
python main.py "Busca ideas value y analiza las 3 mejores"

# Comandos directos (sin orquestador, más rápido)
python main.py --analyst AAPL TEF.MC BATS.L
python main.py --thesis BATS.L --save
python main.py --portfolio status
python main.py --portfolio update_prices
python main.py --screener graham_default
python main.py --tweets AAPL
python main.py --article "Por qué el tabaco sigue siendo value en 2025"

# Modo interactivo
python main.py
```

---

## Fase 4 — Automatización

### Archivos creados

| Archivo | Qué hace |
| ------- | -------- |
| `tools/news_fetcher.py` | Obtiene noticias vía Yahoo Finance RSS, sin APIs de pago. Se añaden al contexto del analyst automáticamente |
| `tools/document_generator.py` | Exporta tesis a `.md` (data/analyses/) y `.docx` con formato profesional (data/reports/) |
| `scheduler.py` | Tareas automáticas: portfolio diario a las 09:00, screener semanal los lunes a las 08:00 |

### Alertas automáticas (scheduler.py)

Las alertas se detectan cuando:

- Precio actual >= target → `TARGET ALCANZADO`
- Precio actual <= stop loss → `STOP LOSS`
- Fondo manual sin actualizar >30 días → `SIN ACTUALIZAR (Nd)`

Los logs se guardan en `data/logs/alerts_YYYY-MM-DD.txt`.

### Comandos del scheduler

```bash
# Ejecutar en background (loop continuo)
python scheduler.py

# Ejecutar tareas manualmente ahora
python scheduler.py --now daily     # Portfolio check + alertas
python scheduler.py --now weekly    # Screener Graham
```

### --save ahora genera archivos reales

```bash
python main.py --thesis BATS.L --save   # → MD + DOCX en data/
python main.py --analyst AAPL --save    # → JSON en data/analyses/
python main.py --screener --save        # → MD report en data/reports/
```

### Pendiente (opcional)

- [ ] Publicación automática en X (tweepy)
- [ ] Publicación automática en Substack (API)

---

## Notas técnicas

- El `client = anthropic.Anthropic()` en `base.py` se inicializa al importar — `load_dotenv()` en `settings.py` debe ejecutarse primero (se garantiza por el orden de imports).
- **DCF v3 — Revenue × Margins → UFCF**: Proyecta revenue futuro, aplica márgenes históricos promedio (gross, SGA, R&D, DA, tax) para construir un P&L simplificado y llegar a UFCF. Maintenance CapEx = DA (el growth CapEx se captura en el revenue growth). Terminal Value con exit multiple por sector. WACC vía CAPM real (beta × equity risk premium + risk-free rate). Escenarios: bear (márgenes peores, WACC+2pp, multiple-3x), base (promedios), bull (márgenes mejores, WACC-1pp, multiple+2x).
- El screener incluye universos predefinidos en `tools/screener_engine.py` (SP500, IBEX35, EUROSTOXX600). Se pueden ampliar con `financedatabase`.
