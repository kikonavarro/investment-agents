---
name: comparator
description: >
  Comparación lado a lado de dos empresas para inversión. Usa esta skill cuando
  el usuario pida comparar dos empresas, elegir entre dos opciones, o un análisis
  "X vs Y". Detectar: "compara", "X vs Y", "cuál es mejor", "diferencias entre",
  "X o Y", "cuál prefieres".
---

# Comparator — Comparación de Empresas

## Principio fundamental

> No se trata de elegir la empresa "perfecta", sino de comparar valor relativo
> con datos concretos y declarar un ganador con justificación clara.

## Paso 0: Obtener los datos

```bash
python main.py --compare TICKER1 TICKER2 --data-only
```

Esto ejecuta el analyst para ambos tickers en paralelo. Si ya existen los JSONs,
puedes leerlos directamente:

- `data/valuations/{TICKER1}/{TICKER1}_valuation.json`
- `data/valuations/{TICKER2}/{TICKER2}_valuation.json`

## Marco de comparación

Evalúa ambas empresas en 7 dimensiones. Para cada una, declara un ganador.

### 1. Valoración (peso: 25%)
- Fair value DCF: calcular los 3 escenarios para ambas (fórmula de thesis-writer)
- Margen de seguridad: ¿cuál ofrece más upside vs precio actual?
- Múltiplos: P/E, EV/EBITDA relativo al crecimiento
- **Ganador**: la que ofrece más margen de seguridad con supuestos razonables

### 2. Calidad del negocio (peso: 20%)
- Modelo de negocio: recurrencia, escalabilidad, pricing power
- Márgenes: bruto, operativo, neto — comparar directamente
- FCF conversion: FCF/Net Income
- **Ganador**: la que tiene márgenes superiores y más predecibles

### 3. Ventaja competitiva (peso: 20%)
- Moat rating: Wide/Narrow/None para cada una
- Fuentes de moat: ¿cuáles son más duraderas?
- ROIC vs WACC: ¿cuál genera más spread?
- **Ganador**: la que tiene moat más ancho y duradero

### 4. Crecimiento (peso: 15%)
- Revenue CAGR histórico (3-5 años)
- Crecimiento proyectado (escenarios del JSON)
- Operating leverage: ¿el crecimiento se traduce en más beneficio?
- **Ganador**: la que crece más con mejor calidad de crecimiento

### 5. Riesgos (peso: 10%)
- Perfil de riesgo: concentración, financiero, competitivo
- Apalancamiento: Debt/EBITDA comparado
- Ciclicidad: ¿cuál es más defensiva?
- **Ganador**: la que tiene menos riesgos materiales

### 6. Capital allocation (peso: 5%)
- ROIC histórico comparado
- Política de dividendos y recompras
- Track record de M&A
- **Ganador**: la que asigna capital de forma más inteligente

### 7. Momentum / Catalizadores (peso: 5%)
- Noticias recientes (del JSON)
- Catalizadores próximos
- Sentimiento del mercado
- **Ganador**: la que tiene catalizadores más claros a 12-24 meses

## Estructura del output

```markdown
## [TICKER1] vs [TICKER2] — Comparación de inversión

### Resumen rápido

| Métrica | [TICKER1] | [TICKER2] |
|---------|-----------|-----------|
| Precio actual | $X.XX | $X.XX |
| Market cap | $X.XB | $X.XB |
| Sector | X | X |
| Fair value (base) | $X.XX | $X.XX |
| Margen de seguridad | +X% | +X% |
| Margen bruto | X% | X% |
| Margen operativo | X% | X% |
| FCF conversion | X% | X% |
| Revenue CAGR 5y | X% | X% |
| Debt/EBITDA | X.Xx | X.Xx |
| ROIC (último año) | X% | X% |
| Moat | Wide/Narrow/None | Wide/Narrow/None |

### Comparación detallada

#### 1. Valoración (25%) — Ganador: [TICKER]
[2-3 frases con datos concretos]

#### 2. Calidad del negocio (20%) — Ganador: [TICKER]
[2-3 frases]

#### 3. Ventaja competitiva (20%) — Ganador: [TICKER]
[2-3 frases]

#### 4. Crecimiento (15%) — Ganador: [TICKER]
[2-3 frases]

#### 5. Riesgos (10%) — Ganador: [TICKER]
[2-3 frases]

#### 6. Capital allocation (5%) — Ganador: [TICKER]
[2-3 frases]

#### 7. Catalizadores (5%) — Ganador: [TICKER]
[2-3 frases]

### Scorecard final

| Dimensión | Peso | [T1] | [T2] |
|-----------|------|------|------|
| Valoración | 25% | X/10 | X/10 |
| Calidad | 20% | X/10 | X/10 |
| Moat | 20% | X/10 | X/10 |
| Crecimiento | 15% | X/10 | X/10 |
| Riesgos | 10% | X/10 | X/10 |
| Capital alloc. | 5% | X/10 | X/10 |
| Catalizadores | 5% | X/10 | X/10 |
| **Total ponderado** | **100%** | **X.X** | **X.X** |

### Veredicto

**Ganador: [TICKER]** — [2-3 frases explicando por qué]

**Cuándo preferir [el otro]**: [1-2 frases sobre en qué escenario el perdedor sería mejor opción]

---
*Comparación generada el [fecha]. No es consejo de inversión.*
```

## Guardar resultado

Guardar en `data/valuations/comparaciones/{T1}_vs_{T2}.md`
Crear directorio si no existe.

## Reglas

1. **Datos del JSON, no inventados** — usa los datos reales de ambas valoraciones
2. **Comparación justa** — misma profundidad para ambas, no sesgar hacia una
3. **Siempre hay un ganador** — empate no vale. Declara ganador aunque sea por poco
4. **Escenario contrario** — siempre incluir cuándo el perdedor sería mejor opción
