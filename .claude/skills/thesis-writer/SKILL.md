---
name: thesis-writer
description: >
  Escribir tesis de inversión value investing completas. Usa esta skill SIEMPRE que
  necesites escribir una tesis, valoración, análisis de empresa, o responder a un
  mensaje del Investment Bot que pida análisis/valoración/tesis de un ticker.
  También aplica cuando el usuario diga "tesis", "valora", "analiza", "DCF",
  "precio objetivo", "fair value", o cualquier variante.
---

# Thesis Writer — Guía completa para escribir tesis de inversión

## Principio fundamental

> Python recoge datos. Tú (Opus) **INTERPRETAS**, decides escenarios, calculas el DCF, y escribes la tesis. Una sola fuente de verdad: la tesis.

## REGLA INQUEBRANTABLE — Calidad sobre velocidad

**NUNCA escribir una tesis mecánica.** Cada tesis requiere el PASO INTERPRETATIVO completo:

1. **LEER el 10-K** (si existe en SEC_filings/) — entender qué pasa realmente en el negocio
2. **BUSCAR CONTEXTO** (WebSearch) — earnings recientes, macro sectorial, commodity prices, competencia
3. **DECIDIR ESCENARIOS con criterio** — tú decides WACC, TV, growth. No hay valores auto-generados
4. **AJUSTAR por tipo de empresa** — MA no es un banco, Tesla no es un fabricante de coches, DE tiene banco cautivo
5. **CONSTRUIR la narrativa ANTES del DCF** — primero entender, luego calcular
6. **Si el DCF diverge >50% del precio** — DETENERSE. Explicar por qué. Si no puedes, los escenarios están mal.

**Máximo 3-4 tesis por sesión.** Una tesis mediocre no vale nada.

## Flujo completo (seguir EN ORDEN)

### Paso 0: Recoger datos

```bash
python main.py --analyst TICKER
```

Genera en `data/valuations/{TICKER}/`:
- `{TICKER}_valuation.json` — datos crudos + métricas de referencia
- `{TICKER}_modelo_valoracion.xlsx` — Excel template DCF
- `SEC_filings/` — 10-K filings (solo EEUU)

El JSON contiene: precio actual, shares outstanding, market cap, sector, industry, business summary,
beta, analyst targets, historical data (revenue, NI, EBITDA, FCF, operating income por año),
latest financials (márgenes, deuda, cash), segments, y `reference_metrics` (márgenes avg históricos,
growth rates YoY, CAGR 3 años, beta, EV/EBITDA, net debt, detecciones de captive finance y adquisiciones).

**El JSON NO contiene escenarios ni fair values.** Tú los decides.

### Paso 0.5: WebSearch para contexto (OBLIGATORIO)

ANTES de decidir escenarios, buscar contexto actualizado:

1. **Earnings recientes**: `"{company} Q{X} FY{YYYY} earnings results"` — ¿beat o miss? ¿guidance?
2. **Macro sectorial**: commodity prices, ciclo de demanda, regulación, aranceles
3. **Competencia/tech**: ¿hay disrupciones, M&A, cambios tecnológicos?

Integrar este contexto en la narrativa y en la decisión de escenarios. Sin contexto macro, los escenarios son ciegos.

### Paso 0.7: Fuentes primarias (OBLIGATORIO)

1. Si existen SEC filings descargados (en `SEC_filings/`), leerlos — especialmente el annual report más reciente
2. Revisar las noticias del JSON
3. Si EV/EBITDA > 30x: buscar presentación de Investor Relations en web

La tesis DEBE citar fuentes (10-K, earnings call, datos macro). Una tesis sin referencias no pasa el review gate.

### Paso 1: Decidir escenarios y calcular DCF

**Tú decides todos los parámetros.** Las `reference_metrics` del JSON son datos de referencia, no inputs directos.

#### 1A. Decidir parámetros con criterio

Para cada escenario (bear/base/bull), decidir:
- **Revenue growth Y1-Y5**: basado en CAGR histórico, analyst estimates, contexto macro, posición en ciclo
- **Márgenes (GM, SGA, R&D, D&A, CapEx, tax)**: usar avg históricos como referencia, ajustar por contexto
- **WACC**: CAPM → Re = risk-free (4%) + beta × ERP (5.5%). Mínimo 10% (filosofía value). Ajustar ±1pp para bear/bull
- **TV Multiple (EV/EBITDA)**: según sector y tipo de empresa:
  - Payment networks (MA, V): 16-24x
  - Tech/SaaS: 16-25x
  - Industrials: 10-14x
  - Hardware (HPQ): 6-10x
  - REITs (VICI): 10-14x + considerar P/FFO
  - Mineras (IVN.TO): NAV-based
  - Pre-profit (NTSK, OSCR): EV/Revenue

**Captive finance** (detectado en `reference_metrics.captive_finance`): usar `net_debt` del JSON (ya ajustada a deuda industrial) en vez de `total_debt`.

#### 1B. Fórmula DCF (por escenario: bear, base, bull)

```
Para cada año Y (1 a 5):
  Revenue_Y = Revenue_anterior × (1 + growth_Y)
  EBIT = Revenue × (gross_margin - sga_pct - rd_pct)
  D&A = Revenue × da_pct
  EBITDA = EBIT + D&A
  UFCF = EBIT × (1 - tax_rate) + D&A - CapEx

Terminal Value = EBITDA_Y5 × TV_multiple
PV(UFCF) = Σ UFCF_Y / (1 + WACC)^Y
PV(TV) = TV / (1 + WACC)^5
Enterprise Value = PV(UFCF) + PV(TV)
Equity Value = EV - Net Debt
Fair Value/acción = Equity Value / shares_outstanding
```

**IMPORTANTE:**
- EBIT ≠ EBITDA. EBITDA = EBIT + D&A. Terminal Value sobre EBITDA.
- UFCF = EBIT×(1-T) + D&A - CapEx. NO restar D&A dos veces.
- Net Debt: usar la ajustada del JSON si hay captive finance.

#### 1C. Gordon Growth como validación (cuando TV >75% del EV)

```
TV_gordon = UFCF_Y5 × (1 + g) / (WACC - g)
```
g = 2.5% default, NUNCA >3.5%. Si diverge >30% del Exit Multiple, investigar.

#### 1D. Fair Value Ponderado

```
Fair Value = 40% × Bear + 40% × Base + 20% × Bull
```

#### 1E. Señal de inversión

Margen de seguridad = (FV Ponderado - Precio) / FV Ponderado:
- ≥40%: 🟢 MUY INFRAVALORADA
- ≥25%: 🟢 INFRAVALORADA
- ≥10%: 🟡 LIGERAMENTE INFRAVALORADA
- ≥-10%: ⚪ VALOR JUSTO
- ≥-25%: 🟠 LIGERAMENTE SOBREVALORADA
- <-25%: 🔴 SOBREVALORADA

#### 1F. Sanity checks (todos deben pasar)

1. **Bear ≈ precio ±15%** — si el bear da mucho upside, eres demasiado optimista
2. **Bull/Bear ratio entre 1.5x y 2.0x**
3. **TV como % del EV** — >85% → validar con Gordon Growth
4. **P/E implícito** — >30x es optimista, <5x es sospechoso
5. **Growth base vs CAGR histórico** — si >1.5× CAGR, justificar
6. **Comparar con consenso** — como contexto, no como análisis principal

### Paso 2: Sub-análisis profundos — OBLIGATORIOS

Cada tesis incluye los 4 sub-análisis. Usar los skills dedicados como referencia:

- **2A. Modelo de negocio** (skill: `business-model`): fuentes de ingreso, unit economics, pricing power, escalabilidad
- **2B. Moat** (skill: `moat-analyst`): 5 fuentes Morningstar, rating Wide/Narrow/No Moat
- **2C. Capital allocation** (skill: `capital-allocation`): ROIC vs WACC, buybacks, dividendos, M&A
- **2D. Riesgos** (skill: `risk-analyst`): top 4-5 riesgos con severidad × probabilidad

### Paso 3: Escribir la tesis

Estructura obligatoria:

1. **Resumen ejecutivo** — precio, fair value, escenarios bear/base/bull como bullets, señal
2. **El negocio** — segmentos, modelo, moat
3. **Análisis financiero** — tabla histórica, tendencias, capital allocation
4. **Valoración DCF** — parámetros, resultados, tabla sensibilidad, análisis de impacto, sanity checks
5. **Riesgos principales** — top 4-5 con severidad y probabilidad
6. **Catalizadores** — positivos y negativos a 12-24 meses
7. **Conclusión y plan de acción** — señal, precio de entrada, posición recomendada

Guardar en `data/valuations/{TICKER}/{TICKER}_tesis_inversion.md`

### Paso 4: Finalizar (OBLIGATORIO)

```bash
# 1. Review gate
python tools/thesis_reviewer.py TICKER

# 2. Guardar fair values + regenerar Excel con escenarios reales
python tools/finalize_thesis.py TICKER thesis_data.json
```

El `thesis_data.json` tiene la estructura:
```json
{
    "fair_values": {"bear": 395, "base": 550, "bull": 760},
    "scenarios": {
        "bear": {
            "revenue_growth_y1": -0.05, "revenue_growth_y2": 0.03, ...,
            "gross_margin": 0.345, "sga_pct": 0.085, "rd_pct": 0.043,
            "da_pct": 0.04, "capex_pct": 0.085, "tax_rate": 0.19,
            "wacc": 0.105, "terminal_multiple": 11
        },
        "base": { ... },
        "bull": { ... }
    }
}
```

Esto guarda los fair values en `history.json` Y regenera el Excel con los escenarios reales para que el usuario pueda jugar con los números.

## Reglas de calidad inquebrantables

1. **Datos exactos** — nunca redondear precios ni cifras
2. **Fair values propios** — siempre calcular los 3 escenarios DCF. El consenso es contexto
3. **Extensión ~2,500-3,000 palabras**
4. **Terminal Value sobre EBITDA** — los múltiplos son EV/EBITDA, no EV/UFCF
5. **Tabla de sensibilidad siempre** — 6-7 WACCs × 5 TV multiples
6. **Análisis de impacto** — qué variable mueve más el precio
7. **Review Gate obligatorio** — `python tools/thesis_reviewer.py TICKER`
8. **Finalizar obligatorio** — `python tools/finalize_thesis.py TICKER thesis_data.json`

## Para mensajes del Investment Bot

Cuando proceses un mensaje de la cola que pide análisis/valoración/tesis:
1. Ejecuta `python main.py --analyst TICKER`
2. Lee el JSON + haz WebSearch de contexto
3. Decide escenarios, calcula DCF, escribe tesis
4. Guarda en `data/valuations/{TICKER}/{TICKER}_tesis_inversion.md`
5. Ejecuta `python tools/thesis_reviewer.py TICKER` — OBLIGATORIO
6. Si PASS → ejecuta `python tools/finalize_thesis.py TICKER thesis_data.json`
7. Envía vía `python tools/check_inbox.py respond <msg_id> tesis.md`
8. Si FAIL → corrige, guarda, repite review (max 2 intentos)
