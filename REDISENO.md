# Rediseño del sistema — Estado y hoja de ruta

> Documento de continuidad entre sesiones. Última actualización: **2026-06-11**.
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
| Overrides `_meta` | `finalize_thesis._normalize_meta`: esquema canónico único (`net_debt_override_m`, `shares_override`, `revenue_base_m`) leído POR IGUAL por la verificación y el Excel, con alias histórico `shares`. La verificación ahora respeta shares + revenue base (antes solo deuda). Migrado WOSG_L a claves canónicas. **Cierra WOSG_L (−10%→+0,1%) y CPAY (+4%→−0,1%).** +9 tests | local |
| Motor con ajustes | `_meta.fv_adjustment = {pct, reason}`: la tesis declara una desviación DELIBERADA sobre el output del motor; la verificación compara contra `motor×(1+pct)`. Si diverge sin declararse, da un mensaje accionable (declara el ajuste o revisa el cálculo) — **informa, no bloquea** (el motor manda sobre la aritmética, no sobre la tesis). `_compare_engine` puro separa cálculo de impresión. +15 tests | local |
| Excel obviado | El modelo `.xlsx` se quita del pipeline (`analyst` y `finalize` ya NO lo generan): era la 3ª copia del DCF y nadie lo consumía (ni el bot ni Kiko). Verificado que nada activo depende de él (el bot no lo envía; email_sender dormido degrada con `if exists`). **Efecto colateral: `finalize` ya no llama a la red.** `excel_generator` se conserva inactivo (reversible). Docs y CLAUDE.md actualizados | local |
| Skill `thesis-writer` | Documentado el flujo real: 3 niveles (supuestos→motor→interpretación), esquema `_meta` canónico (overrides + `fv_adjustment`) y la verificación. Sincronizadas `orchestrator` y `dcf-valuation` (ancladas al motor, no al Excel); `main.py`/CLAUDE.md sin refs muertas. Solo metodología/docs | local |
| Loop cerrado v1 | `tools/watchlist.py` + `python main.py --watchlist`: cruza los fair values guardados con el **precio vivo** (yahooquery batched, 1 llamada) y clasifica cada tesis por MoS (banda value) con triggers de suelo/techo. `classify_signal` extraído a `tools/signals.py` (única fuente; dashboard lo usa). Read-only, lógica pura testeada (179 tests). Escaneó 59 tesis: 9 compra / 10 venta. FV≤0 → N/A. **Auto-detecta tesis con FV extremo desde su finalización (`suspect`, ⚠) → distingue ganga real de FV roto/obsoleto** | local |
| Procesador autónomo | La bandeja la procesa un servicio **launchd** `com.investment.inbox` (cada 60s: pre-check Python gratis con `check_inbox.py count` → si hay mensaje, `claude -p --model opus` con la skill `orchestrator` → responde). **Durable** (sobrevive a cerrar sesión / reinicio), **suscripción** (no API), **coste cero en vacío**. + **watchdog** `com.investment.inbox-watchdog` (avisa por Telegram con causa + comando si se rompe) + helper `~/bin/bandeja` (status/restart/logs). Regla anti-inyección en el prompt. Cierra #8 y el watchdog de #9 | local |

## Qué se ha hecho (sesión 2026-06-11 — auditoría + fiabilidad)

| Fase | Qué | Dónde |
| --- | --- | --- |
| Verificación con razones | `_engine_fair_values` ya **nunca falla en silencio**: devuelve `(fvs, info)` e `info.reason` explica cada None (financiera, JSON roto, campo ausente, input fuera de rango). El caso MA/V (Financial Services se saltaba sin avisar) ahora imprime el porqué y qué hacer. `_dcf_inputs` extraído (preparación de inputs única) | GitHub |
| Motor valida rangos | `DCFAssumptions.__post_init__` caza typos porcentaje-vs-fracción (wacc=10, growth=8) y supuestos imposibles (GM>100 %, tax>60 %, TV>60x) con el campo culpable en el mensaje. NO impone metodología (el floor del WACC sigue siendo juicio) | GitHub |
| Rastro de heurísticas | Peniques GBp, acciones duales y overrides `_meta` dejan nota impresa en cada finalize; la **zona gris del ratio** (ni sano ~1.0 ni corregible) avisa en vez de heredar el error de escala | GitHub |
| Beta con rastro | `financial_data`: beta ausente en Yahoo → `beta_is_default=true` en el JSON + **quality gate** que avisa (un CAPM con beta inventada parece normal sin serlo). 12 checks | GitHub |
| Sensibilidad + reverse-DCF | Cada finalize imprime la tabla WACC±1pt × TV±2x del base y el **crecimiento implícito en el precio** (reverse DCF por bisección): el chequeo anti-optimismo más barato — si tu base asume más growth del que el precio ya descuenta, lo dice | GitHub |
| Track record (semilla #7) | `watchlist.append_snapshot`: cada `--watchlist` acumula una línea JSONL por tesis (`data/watchlist_snapshots.jsonl`, idempotente por día). Materia prima del hit-rate y de la calibración de sesgos. Primer snapshot: 2026-06-11 (65 tesis) | GitHub |
| Limpieza | `valuation_params.yaml` + `WACC_DEFAULTS`/`DCF_DEFAULTS` borrados (config huérfana que nadie leía); `references/dcf_implementation.py` **vaciado** (~950 líneas — era la 2ª implementación del DCF y podía divergir; la skill apunta al motor); cabecera ⛔ DORMIDO en email_sender/pdf_report/document_generator/excel_generator/scheduler; requirements sin streamlit/markdown/rich (cero imports), schedule y python-docx a `requirements-optional.txt`; orchestrator: flag muerto `--data-only` corregido + numeración | GitHub |
| Tests | **217 en verde** (validación de rangos, razones, notas, sensibilidad, reverse-DCF, gate beta, snapshots) | GitHub |

**Estado git:** rama `main`, **pusheado a GitHub** (Kiko autorizó subir el 2026-05-31; antes se mantenía en local). El tag `pre-rediseno-2026` sigue en GitHub como punto de retorno: `git reset --hard pre-rediseno-2026`.

## Cómo retomar (operativo)

- **Intérprete Python:** usar la ruta explícita del proyecto, NO `python3` a secas (resuelve al del sistema sin dependencias):
  `/Users/franciscojaviernavarro/.pyenv/versions/3.12.2/bin/python3`
- **Tests:** `PYBIN -m pytest -q` (deben pasar **217**, a 2026-06-11).
- **Verificar una tesis con el motor** (sin guardar): importar `tools.finalize_thesis._engine_fair_values(scenarios, output_dir, folder, meta)` con `PYTHONPATH="$(pwd)"`.
- **Herramienta de diagnóstico:** el ratio `market_cap/(precio×acciones)` clasifica inconsistencias de datos: ~0.01 = peniques, ~1.0 = sano, >1.5 = acciones duales.

## SIGUIENTE PASO concreto

**#7 Loop cerrado — EN CURSO.** Hecho el escáner on-demand (`--watchlist`). Piezas que faltan:

1. **Alertas automáticas (cierra el loop):** daily scan → avisar (Telegram/Jarvis) cuando una tesis cruza un trigger (entra en compra MoS≥25% o venta ≤-25%, o cruza bear/bull). La primitiva **ya existe**: `notifier.notify_fair_value_cross`. ⚠️ **Toca el scheduler (dormido por decisión) + Telegram → pedir OK a Kiko** y añadir un watchdog (avisar si el loop muere). Decidir: ¿reactivar scheduler vía cron→Claude Code headless, o un loop más simple?
2. **Track record:** ✅ la acumulación ya existe (2026-06-11): cada `--watchlist` guarda snapshot diario en `data/watchlist_snapshots.jsonl` (precio, FV, MoS, señal por tesis). Falta: el ANÁLISIS (hit-rate, calibración de sesgos) cuando haya semanas/meses acumulados.
3. **Sizing por convicción:** tamaño de posición = f(MoS, convicción). La convicción (moat/riesgo) vive en la tesis `.md`, no en `history.json` → hay que parsearla o declararla.

**Otros frentes (independientes):**
- **Re-hacer tesis con FV roto/obsoleto** — el escáner las destapa con ⚠ (`suspect`): **OXY** (FV $228 vs precio $63 — EV/revenue ~12x, imposible; sin `thesis_data.json`), **PYPL**, **CSU_TO**, **HPQ** (FV extremo desde el origen). Más que un `_meta` override, varias piden re-correr la tesis con datos actuales. Es analítico y cambia tesis reales → con criterio de Kiko.
- **Residuos conocidos** PUIG_MC/ITX_MC con `_meta` (rápido).
- **#6 Router de métodos** (DCF/SoP/NAV/… según empresa) — conecta con los FV≤0 (N/A: ASTS, IVN_TO, PLAY) y con TSLA (DCF simple da -252%; pide SoP).

## Residuos catalogados (casos puntuales, no bugs de clase)

| Ticker | Divergencia | Causa | Pendiente |
| --- | --- | --- | --- |
| ~~WOSG_L~~ | ~~−10%~~ → **+0,1%** ✅ | Revenue base en campo ad-hoc; la verificación no lo leía | **RESUELTO** (2026-05-31): `revenue_base_m` canónico + migración del thesis_data |
| PUIG_MC | −43% | IPO reciente, datos ruidosos / supuestos. Es dual-class, pero sin `_meta` | Revisar su tesis: probar `shares_override` y/o `revenue_base_m` con cuentas del informe anual |
| ITX_MC | +102% | Sin override; posible pre-IFRS16 mental o revenue refrescado | Mirar su tesis y declarar el `_meta` adecuado (el esquema ya existe) |

## Roadmap pendiente (fases mayores)

1. ~~**Fix de acciones en la fuente** (`financial_data`)~~ ✅ **HECHO** (2026-05-31): `_reconcile_shares` en `get_company_data` + 10 tests.
2. ~~**Estandarizar overrides** en `_meta` (deuda, revenue base, acciones)~~ ✅ **HECHO** (2026-05-31): `_normalize_meta` + 9 tests; cierra WOSG_L y CPAY.
3. ~~**Motor "manda" con ajustes justificados**~~ ✅ **HECHO** (2026-05-31): `_meta.fv_adjustment` + `_compare_engine`; informa, no bloquea.
4. ~~**`excel_generator` consume del motor**~~ ✅ **RESUELTO de otra forma** (2026-05-31): en vez de hacer que el Excel consuma el motor, se **obvió el Excel** (nadie lo usaba). Eliminada la 3ª copia del DCF → una sola fuente de verdad (motor + verificación).
5. ~~**Skill `thesis-writer`:** documentar el flujo "Opus elige método/múltiplos → motor calcula → Opus interpreta"~~ ✅ **HECHO** (2026-05-31): 3 niveles + esquema `_meta` + verificación; `orchestrator` y `dcf-valuation` sincronizadas.
6. **Router de métodos de valoración** (#4): clasificar la empresa y elegir DCF / SoP / NAV / reverse-DCF / múltiplos / P-Book.
7. **Loop cerrado** (#1, lo que más mueve la aguja) — **EN CURSO:** ✅ escáner watchlist (`--watchlist`, fair value guardado vs precio vivo). Falta: alertas automáticas (cierra el loop), track record (hit-rate), sizing por convicción.
8. ~~**Orquestación proactiva API→suscripción**~~ ✅ **HECHO** (2026-06-01): servicio launchd `com.investment.inbox` → pre-check gratis → `claude -p` headless (Opus) procesa la bandeja con `orchestrator`. Durable, suscripción, coste cero en vacío. Control: `~/bin/bandeja`. (El `scheduler.py` sigue dormido; esto es un poller propio más simple.)
9. **Endurecer el servicio multiusuario** (2 amigos): ✅ watchdog (`com.investment.inbox-watchdog`, avisa por Telegram si el procesador muere/se atasca) + regla anti-inyección en el prompt. **Falta:** rate-limit por usuario, aislamiento más fuerte (Kiko eligió "sin tanto candado" para 3 usuarios de confianza — revisar si se abre a más gente).
10. **Capa de datos completa** (#2): jerarquía de fuentes SEC EDGAR > IR > Yahoo, con reconciliación automática y flags de discrepancia.

## Decisiones de producto ya tomadas (no re-preguntar)

- **Scheduler:** se queda **dormido** (ni activar ni borrar por ahora).
- **Dashboard** (`web_dashboard.py`): **se mantiene** (Kiko lo usa).
- **Email/PDF** (`email_sender`, `pdf_report`, `document_generator`): **se conservan** para reactivar (no borrar).
- **Modelo Excel** (`excel_generator`): **obviado del pipeline** (2026-05-31) — Kiko no lo usa y ningún agente lo consume. El módulo se conserva inactivo por si se reactiva como "render del motor" (no como 3ª copia del DCF). Si se reactiva el email, adjuntará la tesis + SEC sin el Excel (degrada con `if exists`).
- **Servicio a amigos:** 2 personas, solo consumen (tesis, valoraciones, screener, comparativas).

## Arquitectura objetivo (resumen)

`cron/loop → Claude Code (suscripción) = cerebro` · `Python (MCP/herramientas) = datos + motor determinista` · `skills = metodología` · `memoria = calibración`. Todo lo inteligente pasa por la suscripción; Python queda como herramientas tontas y testeadas.
