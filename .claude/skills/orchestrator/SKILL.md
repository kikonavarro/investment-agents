---
name: orchestrator
description: >
  Orquestador de mensajes del Investment Bot y peticiones de inversión. Usa esta skill
  SIEMPRE que recibas un mensaje de la cola de Telegram (check_inbox.py) o cuando el
  usuario pida algo relacionado con inversiones y necesites decidir qué ejecutar.
  Determina el tipo de petición y ejecuta el pipeline correcto.
---

# Orchestrator — Routing de peticiones de inversión

## Cómo funciona

Cuando llega un mensaje (del usuario o de la cola del Investment Bot), identifica qué pide
y ejecuta el pipeline correspondiente. No necesitas llamar a la API de Anthropic — tú eres
el orquestador Y el ejecutor.

## Regla fundamental — LEER ANTES DE EJECUTAR

Antes de ejecutar cualquier pipeline, DEBES:
1. **Leer la skill correspondiente** (con Skill tool o leyendo el SKILL.md directamente)
2. **Leer los feedback memories relevantes** (si aplican al tipo de petición)
3. Solo entonces ejecutar

**NUNCA** escribas una tesis sin leer `thesis-writer` + `dcf-valuation`.
**NUNCA** generes tweets sin leer `tweet-generator`.
**NUNCA** hagas un screener sin leer `screener-ranking`.
**NUNCA** escribas un artículo sin leer `content-writer`.

## Skills disponibles

| Skill | Cuándo usarla |
|-------|---------------|
| `thesis-writer` | Tesis, valoración, análisis DCF, fair value |
| `moat-analyst` | Ventaja competitiva, moat, barreras de entrada |
| `risk-analyst` | Riesgos materiales, perfil de riesgo |
| `business-model` | Modelo de negocio, cómo gana dinero, unit economics |
| `capital-allocation` | ROIC, dividendos, recompras, M&A, gestión de deuda |
| `comparator` | Comparación lado a lado de dos empresas |
| `thesis-reviewer` | Revisar/comparar tesis externa vs la nuestra |
| `ir-auditor` | Auditar cifras del IR vs cuentas oficiales (detectar maquillaje) |
| `screener-ranking` | Ranking cualitativo de candidatas value |
| `tweet-generator` | Hilos Twitter/X sobre inversiones |
| `content-writer` | Artículos Substack/blog |
| `leaps-finder` | LEAPS calls ITM (delta 0.60-0.80, >12m). Modo daily o on-demand sobre un ticker |
| `dcf-valuation` | Referencia teórica de metodología DCF |
| `thesis_reviewer.py` | Review gate automático antes de enviar (Python) |

**IMPORTANTE:** Toda tesis incluye SIEMPRE los 4 sub-análisis (moat, riesgos, modelo de negocio, capital allocation). No hay modo "light". Si se añade una nueva skill, actualizar esta tabla.

### Regla especial: Empresas con EV/EBITDA > 50x (valoración extrema)

Para estas empresas, el pipeline estándar NO es suficiente. El DCF mecánico producirá resultados absurdos (ej: Tesla $15 vs $362). **OBLIGATORIO:**

1. Ejecutar `python main.py --analyst TICKER`
2. **LEER el quality gate output** — si dice `valoracion_extrema`, la empresa cotiza a múltiplos elevados
3. **Diseñar escenarios con criterio** — TV multiples de 20-35x (tech/growth) si aplica
4. **Usar Sum-of-Parts** si la empresa tiene negocios de opcionalidad:
   - Negocio actual (DCF con parámetros realistas)
   - + Opcionalidad (ej: FSD/Robotaxi para Tesla, AI platform para IREN)
   - = Fair value total más realista
5. **NUNCA presentar solo el DCF puro** sin contextualizar la diferencia vs mercado
6. El thesis reviewer FALLARÁ si el fair value es <5% del precio — esto es intencionado para forzar revisión manual

## Routing de peticiones

### 1. Valoración / Análisis / Tesis
**Skills a invocar:** `thesis-writer` + `dcf-valuation` (referencia) + feedbacks DCF
**Detectar:** "analiza", "valora", "tesis", "valoración", "DCF", "precio objetivo",
"fair value", "cuánto vale", "dame la valoración de"

**Pipeline:**
```bash
python main.py --analyst TICKER ```
Luego:
1. Leer `data/valuations/{TICKER}/{TICKER}_valuation.json`
2. **Buscar Investor Relations** — buscar en web la presentación de resultados anuales
   y el annual report. Descargar PDFs y guardar en `data/valuations/{TICKER}/IR/`
3. **Ejecutar IR Auditor** (skill `ir-auditor`) — comparar cifras del IR con las de Yahoo
   y las cuentas oficiales. Detectar maquillaje: EBITDA ajustado vs reported, IFRS16,
   deuda excluida, FCF inflado. Guardar auditoría en `data/valuations/{TICKER}/IR/ir_audit_{fecha}.md`
4. Escribir la tesis usando AMBAS fuentes (Yahoo + IR ajustado) siguiendo `thesis-writer`

**Guardar en:** `data/valuations/{TICKER}/{TICKER}_tesis_inversion.md`

**Review Gate:** Después de guardar, ejecutar `python tools/thesis_reviewer.py TICKER`.
Si da FAIL, corregir y reintentar (max 2x). Ver sección "Flujo completo" paso 8.

### 2. Screener (buscar ideas)
**Skill a invocar:** `screener-ranking`
**Detectar:** "busca ideas", "screener", "empresas infravaloradas", "qué comprar",
"oportunidades value", "busca candidatas"

**Pipeline:**
```bash
python main.py --screener graham_default ```
Luego evaluar las candidatas siguiendo la skill `screener-ranking`.

**Filtros disponibles:** `graham_default`, `value_aggressive`, `bargain_hunter`

### 3. Tweets / Redes sociales
**Skill a invocar:** `tweet-generator`
**Detectar:** "tweet", "hilo", "twitter", "redes sociales", "publica sobre"

**Pipeline:**
Si hay datos de valoración del ticker → usar el JSON existente.
Si no → ejecutar `python main.py --analyst TICKER --data-only` primero.
Luego generar el hilo siguiendo la skill `tweet-generator`.

### 4. Noticias
**Detectar:** "noticias", "qué pasa con", "novedades", "actualidad de"

**Pipeline:**
```bash
python main.py --analyst TICKER ```
El analyst ya descarga noticias vía RSS. Leer el JSON y resumir las noticias relevantes.

### 5. Portfolio / Cartera
**Detectar:** "cartera", "portfolio", "mis posiciones", "cómo va mi cartera"

**Pipeline:**
```bash
python main.py --portfolio status
```
Leer directamente `data/mi_cartera.xlsx` con Python e interpretar tú.

### 6. Artículo Substack
**Skill a invocar:** `content-writer`
**Detectar:** "artículo", "escribe un artículo", "substack", "post"

**Pipeline:**
Ejecutar analyst si no hay datos. Luego escribir el artículo siguiendo la skill `content-writer`.

### 7. Comparación de empresas
**Skill a invocar:** `comparator`
**Detectar:** "compara", "X vs Y", "cuál es mejor", "diferencias entre"

**Pipeline:**
```bash
python main.py --compare TICKER1 TICKER2 ```
Ejecuta analyst para ambos tickers en paralelo.
Leer los dos JSONs y comparar siguiendo la skill `comparator`.

### 8. Revisión de tesis externa
**Skill a invocar:** `thesis-reviewer`
**Detectar:** "analiza esta tesis", "compara con tu tesis", "qué opinas de este análisis",
archivo adjunto con tesis (PDF/Excel), "[Archivo: ...]" en el texto del mensaje

**Pipeline:**
1. Leer el archivo adjunto (PDF con Read tool, Excel con openpyxl)
2. Identificar el ticker de la empresa analizada
3. Leer nuestra tesis si existe: `data/valuations/{TICKER}/{TICKER}_tesis_inversion.md`
4. Si no existe nuestra tesis, ejecutar `python main.py --analyst TICKER --data-only` primero
5. Comparar siguiendo la skill `thesis-reviewer`
6. Guardar en `data/valuations/{TICKER}/review_{fuente}_{fecha}.md`

### 9. Sub-análisis individuales (antes #8)
Las skills dedicadas se pueden invocar de forma independiente:

| Petición | Skill |
|----------|-------|
| "moat de X", "ventaja competitiva de X", "barreras de entrada de X" | `moat-analyst` |
| "riesgos de X", "qué riesgos tiene X" | `risk-analyst` |
| "modelo de negocio de X", "cómo gana dinero X" | `business-model` |
| "capital allocation de X", "dividendos de X", "recompras de X" | `capital-allocation` |

**Pipeline:** Ejecutar `python main.py --analyst TICKER --data-only` si no hay JSON, luego aplicar el skill correspondiente.

### 9. Mensaje del scheduler [SCHEDULER]
Los mensajes del scheduler llevan el tag `[SCHEDULER]` al inicio.

- `[SCHEDULER] Genera un hilo de tweets` → skill `tweet-generator`
- `[SCHEDULER] Screener semanal` → skill `screener-ranking`
- `[SCHEDULER] LEAPS scan` → skill `leaps-finder` (modo daily)
- Otros → interpretar el contenido y actuar

### 10. LEAPS / Opciones largo plazo
**Skill a invocar:** `leaps-finder`
**Detectar:** "leaps", "leap call", "buena leap", "options largo plazo", "call largo plazo en X",
"qué leap puedo comprar", o pregunta sobre call ITM en un ticker concreto.

**Pipeline (on-demand):**
```bash
python -m tools.leaps_scanner TICKER
```
Interpretar el JSON y responder según skill `leaps-finder` modo on-demand.

**Pipeline (daily, mensaje [SCHEDULER] LEAPS):**
El scheduler ya generó el scan. Leer top candidatos del mensaje, elegir 4-5 mejores
y enviar mensaje con justificación corta para cada una.

## Resolución de tickers

- **USA conocidos:** Amazon→AMZN, Apple→AAPL, Google→GOOGL, Meta→META,
  Microsoft→MSFT, Tesla→TSLA, Nvidia→NVDA, Deere→DE
- **España:** añadir `.MC` (Inditex→ITX.MC, Telefónica→TEF.MC, Santander→SAN.MC)
- **Otros mercados:** consultar Yahoo Finance para el sufijo correcto
  (.L Londres, .TO Toronto, .AX Australia, .PA París, .DE Frankfurt)
- **Si no estás seguro del ticker:** usa el nombre de la empresa,
  `get_company_data()` intentará resolverlo

## Flujo completo para un mensaje del Investment Bot

```
1. python tools/check_inbox.py          → ver mensaje pendiente
2. Identificar tipo de petición          → este documento
3. Ejecutar pipeline Python              → --data-only (gratis)
4. Leer datos generados                  → JSON/Excel
5. Leer skills según tipo (OBLIGATORIO):
   - Tesis/valoración → thesis-writer + dcf-valuation + feedbacks DCF
   - Screener         → screener-ranking
   - Tweets           → tweet-generator
   - Artículo         → content-writer
6. Escribir respuesta con skill          → thesis-writer / screener / tweets
7. Guardar respuesta                     → data/valuations/{TICKER}/ si aplica
8. REVIEW GATE (solo tesis/valoraciones):
   a. python tools/thesis_reviewer.py TICKER
   b. Si FAIL → corregir escenarios/cálculos → reintentar (max 2x)
   c. Si REVIEW → leer warnings, decidir si corregir
   d. Si PASS → continuar
   e. Checklist cualitativo:
      - ¿DCF propio (no solo consenso analistas)?
      - ¿3 precios claros con supuestos?
      - ¿Fair value ponderado 40/40/20?
      - ¿Tabla sensibilidad con valores reales?
      - ¿Conclusión con recomendación clara?
9. python tools/check_inbox.py respond <id> --text "respuesta"
10. Investment Bot envía al amigo        → automático (siguiente poll)
```

## Mensajes ambiguos

Si el mensaje no encaja en ninguna categoría clara:
- Preguntas generales sobre una empresa → ejecutar analyst + resumen breve
- "Qué opinas de X" → analyst + mini-tesis (resumen ejecutivo + conclusión)
- Saludos / off-topic → responder cortésmente que eres un bot de inversión
