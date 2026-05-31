# Rediseño del sistema — Estado y hoja de ruta

> Documento de continuidad entre sesiones. Última actualización: **2026-05-31**.
> Si retomas el rediseño, **lee esto primero**. El detalle conceptual está aquí;
> el estado resumido y el siguiente paso también están en la memoria persistente.

## Objetivo (lo que pidió Kiko)

Rehacer el sistema con cinco metas:

1. **Maximizar el beneficio** de sus inversiones en acciones.
2. **Información siempre fiable y útil.**
3. Crear **tesis** y estimar **valor intrínseco**.
4. **No solo value** (Graham/Buffett): usar el método mejor según la empresa y el riesgo-beneficio.
5. Tirar **siempre de la suscripción** (Claude Code), **nunca de la API** (no gastar).
6. Puede dejar un **ordenador encendido 24 h**.

## Principios de diseño ACORDADOS (no cambiar sin consultar)

- **Tres niveles de responsabilidad:**
  1. **Supuestos** (crecimiento, márgenes, WACC, múltiplos, qué método) → los decide **Opus** (juicio).
  2. **Aritmética** (proyectar, descontar, TV, equity, fair value) → la hace el **motor** (código determinista y testeado).
  3. **Interpretación y recomendación** (qué significa el número, ajustes cualitativos, comprar/esperar/evitar, convicción) → **Opus** otra vez.
- **El motor NO manda sobre la tesis.** Manda sobre la aritmética. El número del motor es el "valor de Graham" (punto de partida); la decisión final es estilo Buffett (integra moat, riesgos, calidad, margen de seguridad).
- **La tesis no es una cuenta.** Opus puede desviarse del número del motor, pero la desviación debe ser un **ajuste deliberado y justificado por escrito** (p. ej. "+10% por opcionalidad X"), nunca un error de cálculo silencioso. Esa es justo la diferencia que el motor caza.
- **El motor no se aplica a ciegas.** Opus elige el método: DCF exit-multiple, Sum-of-Parts, NAV, reverse-DCF, P/Book… Las financieras/REITs NO se valoran por este DCF.
- **Causa raíz, no parches** (regla de Kiko). Arreglar en la fuente, no rodear el problema.
- **Nunca cambiar flujo/datos sin consultar** (regla de Kiko). Especialmente lo que toca el bot de Telegram (producción, lo usan 2 amigos).

## Qué se ha hecho (sesión 2026-05-31)

| Fase | Qué | Dónde |
| --- | --- | --- |
| Red de seguridad | Tag `pre-rediseno-2026` (punto de retorno) + se versionaron las 15 skills | **GitHub** |
| Limpieza | Borrados huérfanos (`agents/content_writer`, `social_media`, `thesis_writer`, `news_fetcher`, `orchestrator`), constantes de API muertas, dependencia `anthropic`, funciones muertas (`format_*_for_llm`, etc.) | local |
| Motor | `tools/valuation_engine.py` (DCF exit-multiple sobre EBITDA, puro, determinista) + `tests/test_valuation_engine.py` (18 tests, golden FV=46.25) | local |
| Validación | El motor reproduce las tesis DCF-estándar con <2% (AAPL, MELI, AMD, RMS_PA, MC_PA…) | — |
| Integración v1 | `finalize_thesis._engine_fair_values` verifica en cada finalización y muestra la comparación tesis vs motor. **Solo informa** (no manda ni bloquea) | local |
| Fiabilidad de datos | En la verificación: detector de escala `market_cap/(precio×acciones)` → peniques UK (×100), financieras (no-DCF), acciones duales (`market_cap/precio`), override de deuda (`_meta.net_debt_override_m`) | local |
| Fix en la fuente | `financial_data._reconcile_shares`: la corrección de acciones duales (ratio>1.5 → `market_cap/precio`) ahora nace en `get_company_data`, no solo en la verificación. Toda valoración (Excel, JSON, dashboard) parte de las acciones reales. Helper puro + 10 tests. Preserva el valor crudo en `shares_reconciliation` (traza, nada oculto). Idempotente con la verificación | local |

**Estado git:** rama `main`, ~6 commits en **local sin pushear** (decisión de Kiko: no subir aún). El tag `pre-rediseno-2026` sí está en GitHub. Para volver atrás: `git reset --hard pre-rediseno-2026`.

## Cómo retomar (operativo)

- **Intérprete Python:** usar la ruta explícita del proyecto, NO `python3` a secas (resuelve al del sistema sin dependencias):
  `/Users/franciscojaviernavarro/.pyenv/versions/3.12.2/bin/python3`
- **Tests:** `PYBIN -m pytest -q` (deben pasar **128**).
- **Verificar una tesis con el motor** (sin guardar): importar `tools.finalize_thesis._engine_fair_values(scenarios, output_dir, folder, meta)` con `PYTHONPATH="$(pwd)"`.
- **Herramienta de diagnóstico:** el ratio `market_cap/(precio×acciones)` clasifica inconsistencias de datos: ~0.01 = peniques, ~1.0 = sano, >1.5 = acciones duales.

## SIGUIENTE PASO concreto

**Estandarizar los overrides de `_meta`** (#2 del roadmap) con un esquema único que **tanto el Excel como la verificación** respeten. Hoy conviven overrides ad-hoc que la verificación (`_engine_fair_values`) no siempre lee:

- `_meta.net_debt_override_m` (deuda) — lo leen finalize y el Excel. ✅
- `_meta.shares_override` — lo lee el Excel (`finalize_thesis.py:299`) pero **NO** la verificación → posible divergencia.
- Revenue base ad-hoc tipo `_meta.revenue_base_fy26_gbp_m` (caso **WOSG_L**, −10%) — la verificación no lo lee → divergencia.

Objetivo: un esquema `_meta` documentado (deuda, revenue base, acciones) leído por ambos caminos, para cerrar los residuos **WOSG_L** e **ITX_MC**. Con tests. No toca el bot en producción (solo finalize + verificación), pero confirmar el esquema con Kiko antes de migrar las tesis existentes.

## Residuos catalogados (casos puntuales, no bugs de clase)

| Ticker | Divergencia | Causa | Pendiente |
| --- | --- | --- | --- |
| WOSG_L | −10% | Revenue base en campo ad-hoc `_meta.revenue_base_fy26_gbp_m` que la verificación no lee | Estandarizar el esquema de `_meta` (revenue override genérico) |
| PUIG_MC | −44% | IPO reciente, datos ruidosos / supuestos | Revisar datos y supuestos de la tesis |
| ITX_MC | +102% | Sin override; posible pre-IFRS16 mental o revenue refrescado | Mirar su tesis y decidir override |

## Roadmap pendiente (fases mayores)

1. ~~**Fix de acciones en la fuente** (`financial_data`)~~ ✅ **HECHO** (2026-05-31): `_reconcile_shares` en `get_company_data` + 10 tests.
2. **Estandarizar overrides** en `_meta` (deuda, revenue base, acciones) con esquema único — **el siguiente paso de arriba**.
3. **Motor "manda" con ajustes justificados:** permitir que una tesis declare un ajuste explícito sobre el DCF puro, para que la verificación no lo marque como error.
4. **`excel_generator` consume del motor** — eliminar el tercer sitio donde hoy se recalcula el DCF (una sola fuente de verdad).
5. **Skill `thesis-writer`:** documentar el flujo "Opus elige método/múltiplos → motor calcula → Opus interpreta y recomienda". (Recordar: sincronizar `orchestrator` al tocar skills.)
6. **Router de métodos de valoración** (#4): clasificar la empresa y elegir DCF / SoP / NAV / reverse-DCF / múltiplos / P-Book.
7. **Loop cerrado** (#1, lo que más mueve la aguja): track record de tesis (¿acertó el fair value?), watchlist con triggers de compra/venta, sizing por convicción.
8. **Orquestación proactiva API→suscripción** (#5): el `scheduler.py` está apagado pero listo (encola para Claude Code, sin API). Activarlo vía cron→Claude Code headless.
9. **Endurecer el servicio multiusuario** (2 amigos): rate-limit por usuario, aislamiento anti-inyección de prompts, watchdog que avise (por Jarvis) si el loop de la cola muere.
10. **Capa de datos completa** (#2): jerarquía de fuentes SEC EDGAR > IR > Yahoo, con reconciliación automática y flags de discrepancia.

## Decisiones de producto ya tomadas (no re-preguntar)

- **Scheduler:** se queda **dormido** (ni activar ni borrar por ahora).
- **Dashboard** (`web_dashboard.py`): **se mantiene** (Kiko lo usa).
- **Email/PDF** (`email_sender`, `pdf_report`, `document_generator`): **se conservan** para reactivar (no borrar).
- **Servicio a amigos:** 2 personas, solo consumen (tesis, valoraciones, screener, comparativas).

## Arquitectura objetivo (resumen)

`cron/loop → Claude Code (suscripción) = cerebro` · `Python (MCP/herramientas) = datos + motor determinista` · `skills = metodología` · `memoria = calibración`. Todo lo inteligente pasa por la suscripción; Python queda como herramientas tontas y testeadas.
