---
name: capital-allocation
description: >
  Análisis de asignación de capital de empresas. Usa esta skill cuando necesites
  evaluar cómo una empresa usa su capital: reinversión, dividendos, recompras, M&A,
  gestión de deuda. Se ejecuta SIEMPRE como parte de cualquier tesis de inversión.
  También se puede invocar de forma independiente con "capital allocation de X",
  "cómo asigna capital X", "dividendos y recompras de X", "M&A de X".
---

# Capital Allocation Analyst — Análisis de Asignación de Capital

## Principio fundamental

> "La asignación de capital es la habilidad más importante de un CEO. Una empresa que
> genera $1B en FCF pero lo asigna mal vale menos que una que genera $500M y lo invierte
> brillantemente." — Inspirado en The Outsiders (William Thorndike)

## Paso 0: Obtener los datos

Si no existe `data/valuations/{TICKER}/{TICKER}_valuation.json`:
```bash
python main.py --analyst TICKER --data-only
```

Lee el JSON. Necesitas: historical_data (revenue, net_income, fcf, ebitda, operating_income por año),
latest_financials (total_debt, cash, total_equity), scenarios (wacc), business_summary.

## Marco de análisis

### 1. ROIC vs WACC — ¿Genera valor la empresa?

El test fundamental: ¿cada dólar reinvertido genera más que el coste de capital?

**Calcular ROIC** (para cada año disponible en historical_data):
```
ROIC = NOPAT / Invested Capital
NOPAT = Operating Income × (1 - tax_rate)
Invested Capital = Total Equity + Total Debt - Cash
```

Valores del JSON:
- Operating Income: `historical_data[year]["operating_income"]`
- Tax rate: usar `scenarios["base"]["tax_rate"]`
- Equity, Debt, Cash: `latest_financials`

**Interpretación**:
| ROIC vs WACC | Significado |
|---|---|
| ROIC > WACC + 5pp consistente | Excelente allocator, genera mucho valor |
| ROIC > WACC consistente | Buen allocator, genera valor |
| ROIC ≈ WACC | Neutral, no genera ni destruye |
| ROIC < WACC | Destruye valor, mala asignación |

**Tendencia**: ¿ROIC mejorando o deteriorándose? La tendencia importa más que el nivel absoluto.

### 2. Usos del Free Cash Flow

Clasifica cómo distribuye la empresa su FCF. Idealmente necesitas info adicional
(buscar en web si es empresa conocida), pero puedes inferir mucho del JSON:

#### a) Reinversión orgánica (CapEx + R&D)
- **CapEx/Revenue**: ¿cuánto reinvierte en el negocio?
  - Usar `scenarios["base"]["capex_pct"]` y `scenarios["base"]["rd_pct"]`
  - CapEx crecimiento = CapEx total - Depreciation (D&A). Si CapEx >> D&A → invirtiendo en crecer
  - Si CapEx ≈ D&A → solo mantenimiento, no crecimiento orgánico
- **R&D intensity**: R&D/Revenue
  - >10% → empresa innovadora (tech, farma)
  - 3-10% → inversión moderada
  - <3% → bajo, ¿suficiente para mantener competitividad?
- **Retorno de la reinversión**: ¿El revenue crece cuando sube el capex/R&D?
  - Calcular correlación simple: ¿años con más capex → más crecimiento después?

#### b) Dividendos
- **Payout ratio**: Dividendo / FCF (mejor que Dividendo / EPS)
  - <40% → sostenible, margen para crecer
  - 40-70% → razonable para empresa madura
  - >70% → ¿sostenible? Comprobar si FCF es consistente
- **Crecimiento del dividendo**: CAGR últimos 5 años (buscar online)
- **Dividend yield**: precio actual vs dividendo
- **Track record**: ¿Cuántos años consecutivos aumentando? (Dividend Aristocrats = 25+)

#### c) Recompras de acciones
- **¿Reducen dilución real?** Comprobar: ¿shares outstanding baja año a año?
  - Si SBC (stock-based compensation) alta y shares no bajan → recompras solo compensan dilución
  - Si shares outstanding baja 2-3% anual → recompras netas efectivas
- **Timing**: ¿Recompran a precios razonables o en máximos?
  - Señal negativa: recompras récord en año con valoración máxima
  - Señal positiva: recompras aceleradas en caídas del mercado
- **Calcular**: shares_outstanding trend (necesita datos multi-año, puede estar en info)

#### d) M&A (Fusiones y adquisiciones)
- **Track record**: ¿Las adquisiciones generaron valor o destruyeron?
  - Goodwill/Total Assets: si >30% → muchas adquisiciones, ¿a qué precio?
  - ¿Los márgenes mejoraron o empeoraron post-adquisición?
- **Tipo de M&A**:
  - Bolt-on (pequeñas, complementarias) → generalmente positivo
  - Transformacional (grandes, cambio de modelo) → alto riesgo
  - Serial acquirer (Constellation Software, Danaher) → evaluar disciplina
- **Fuente**: business_summary puede mencionar adquisiciones recientes. Buscar web para detalle.

#### e) Gestión de deuda
- **Nivel**: Debt/EBITDA y Debt/Equity (de latest_financials)
  - <1x Debt/EBITDA → conservador
  - 1-3x → moderado
  - >3x → agresivo
- **Coste**: ¿Deuda a tipo fijo o variable? ¿Vencimientos próximos?
- **Uso**: ¿Deuda para financiar crecimiento rentable o para cubrir huecos?
- **Cash neto**: Si Cash > Debt → posición de caja neta (fortaleza)

### 3. Score de Capital Allocation

| Criterio | Excelente (3) | Bueno (2) | Mediocre (1) | Malo (0) |
|---|---|---|---|---|
| ROIC vs WACC | >WACC+5pp, 5 años | >WACC, 5 años | ≈WACC | <WACC |
| Reinversión | CapEx con retorno probado | CapEx moderado con retorno | Capex sin retorno claro | Sobreinversión sin retorno |
| Dividendos | Payout sostenible, creciente | Payout razonable, estable | Payout alto, sin crecimiento | Insostenible o cortado |
| Recompras | Reducen shares a precios razonables | Netas positivas | Compensan SBC solamente | Destruyen valor (timing pésimo) |
| M&A | Track record excelente | Generalmente acertivo | Mixto | Destruye valor |
| Deuda | Conservadora, bien usada | Moderada | Algo alta | Excesiva |

**Score total**: Suma / 18 puntos máximos → porcentaje

## Estructura del output

```markdown
### Asignación de capital

**ROIC vs WACC**:
| Año | ROIC | WACC | Spread |
|-----|------|------|--------|
| 20XX | X.X% | X.X% | +X.Xpp |
| ... | ... | ... | ... |

Promedio ROIC X.X% vs WACC X.X% → [genera/destruye valor]. Tendencia: [mejorando/estable/deteriorándose].

**Distribución del FCF**:
- Reinversión (CapEx + R&D): ~X% del revenue — [agresivo/moderado/conservador]
- Dividendos: payout X% del FCF, yield X% — [sostenible/en riesgo]
- Recompras: shares outstanding [bajando X% anual / estables / subiendo]
- M&A: [activo/selectivo/inactivo] — track record [bueno/mixto/malo]
- Deuda: X.Xx Debt/EBITDA — [conservador/moderado/agresivo]

**Calidad del management como allocator**: [Excelente/Bueno/Mediocre/Malo]
[1-2 frases justificativas con datos]
```

## Reglas inquebrantables

1. **ROIC siempre** — es el test fundamental. Sin ROIC no hay análisis de capital allocation
2. **Datos reales** — calcula ROIC desde el JSON, no inventes números
3. **Contexto sectorial** — CapEx/Revenue de 15% es normal en industrials pero alto en software
4. **Tendencia > nivel** — ROIC bajando de 25% a 15% es peor que ROIC estable en 12%
5. **M&A requiere investigación** — el JSON no tiene detalle de adquisiciones. Buscar si es empresa relevante
