---
name: moat-analyst
description: >
  Análisis de ventaja competitiva (moat) de empresas. Usa esta skill cuando
  necesites evaluar el moat, ventaja competitiva, barreras de entrada, o
  posición competitiva de una empresa. Se ejecuta SIEMPRE como parte de
  cualquier tesis de inversión. También se puede invocar de forma independiente
  con "moat de X", "ventaja competitiva de X", "barreras de entrada de X".
---

# Moat Analyst — Análisis de Ventaja Competitiva

## Principio fundamental

> "La clave de la inversión no es evaluar cuánto va a afectar una industria a la sociedad,
> sino determinar la ventaja competitiva de una empresa y, sobre todo, la durabilidad de esa ventaja."
> — Warren Buffett

## Paso 0: Obtener los datos

Si no existe `data/valuations/{TICKER}/{TICKER}_valuation.json`:
```bash
python main.py --analyst TICKER --data-only
```

Lee el JSON. Necesitas: business_summary, sector, industry, segments, historical_data (márgenes, revenue),
latest_financials (gross_margin, operating_margin, net_margin).

## Framework: Las 5 fuentes de moat (Morningstar/Buffett)

Evalúa CADA una como **Fuerte / Moderada / Débil / Ausente** con evidencia concreta.

### 1. Switching Costs (Costes de cambio)
- ¿Cuánto le cuesta al cliente cambiar a un competidor? (dinero, tiempo, riesgo)
- Tipos: contractuales, técnicos (integración), de aprendizaje, emocionales (marca)
- **Evidencia cuantitativa**: tasa de retención de clientes, churn rate, duración media de contratos
- **Señales fuertes**: revenue recurrente >60%, contratos multi-año, integración profunda en el workflow del cliente
- **Señales débiles**: producto commodity, fácil de replicar, sin lock-in técnico

### 2. Network Effects (Efectos de red)
- ¿Más usuarios = mejor producto/servicio?
- Tipos: directos (marketplace), indirectos (plataforma + desarrolladores), de datos (más datos = mejor producto)
- **Evidencia**: crecimiento exponencial de usuarios, winner-take-most en su categoría, ratio usuarios/competidor
- **Señales fuertes**: marketplace dominante, plataforma con ecosistema, datos propietarios
- **Señales débiles**: producto funciona igual con 1 o 1M usuarios

### 3. Intangible Assets (Activos intangibles)
- **Marcas**: ¿permite pricing premium? Medir: margen bruto vs competidores, brand loyalty
- **Patentes**: ¿protección real? Duración, geografía, facilidad de workaround
- **Licencias regulatorias**: ¿barrera de entrada regulatoria? Ej: banca, telecom, farmacéutica
- **Know-how**: ¿expertise difícil de replicar? Ej: procesos de fabricación, algoritmos propietarios
- **Evidencia**: premium de precio vs competidores, cuota de mercado estable, márgenes superiores al sector

### 4. Cost Advantages (Ventajas en costes)
- **Economías de escala**: coste unitario disminuye con volumen
- **Acceso privilegiado a recursos**: materias primas, ubicación, talento
- **Procesos superiores**: eficiencia operativa, tecnología propia
- **Evidencia**: márgenes operativos consistentemente superiores al sector, coste de producción más bajo
- **Cuidado**: las ventajas en costes son las más fáciles de erosionar con tecnología nueva

### 5. Efficient Scale (Escala eficiente)
- ¿El mercado es lo suficientemente pequeño como para no atraer nuevos competidores?
- Natural monopoly/oligopoly: infraestructura (pipelines, redes, aeropuertos)
- **Evidencia**: pocos players con cuota estable durante años, nuevos entrantes no logran rentabilidad
- **Señales fuertes**: regulación que limita competencia, inversión inicial prohibitiva

## Evaluación cuantitativa del moat

### Métricas obligatorias (calcular desde historical_data del JSON)

1. **Estabilidad de márgenes brutos** (5 años):
   - Desviación estándar < 3pp → moat fuerte
   - Desviación estándar 3-6pp → moat moderado
   - Desviación estándar > 6pp → moat débil o ausente

2. **ROIC vs WACC** (calcular):
   - ROIC = EBIT × (1 - tax) / (Total Equity + Total Debt - Cash)
   - Si ROIC > WACC sostenido 5+ años → evidencia de moat
   - Si ROIC > 15% sostenido → moat muy probable
   - Si ROIC < WACC → destrucción de valor, no hay moat

3. **Tendencia de márgenes operativos**:
   - Crecientes o estables → moat protege pricing power
   - Decrecientes → moat en erosión o ausente

4. **Market share** (buscar si disponible):
   - Estable o creciente → moat funciona
   - Decreciente → presión competitiva, moat erosionándose

## Rating final del moat

Basándote en las 5 fuentes + evidencia cuantitativa, asigna:

| Rating | Criterio |
|--------|----------|
| **Wide Moat** | ≥2 fuentes fuertes, ROIC > WACC sostenido, márgenes estables/crecientes |
| **Narrow Moat** | 1 fuente fuerte o ≥2 moderadas, ROIC > WACC la mayoría de años |
| **No Moat** | Sin fuentes claras, ROIC ≈ WACC, márgenes bajo presión |

## Estructura del output

```markdown
### Ventaja competitiva (Moat)

**Rating: [Wide/Narrow/No Moat]**

| Fuente | Evaluación | Evidencia |
|--------|------------|-----------|
| Switching costs | Fuerte/Moderada/Débil/Ausente | 1-2 frases con datos |
| Network effects | ... | ... |
| Intangibles | ... | ... |
| Cost advantages | ... | ... |
| Efficient scale | ... | ... |

**Evidencia cuantitativa:**
- ROIC promedio 5 años: X% vs WACC X% → [genera/destruye valor]
- Margen bruto: X% ± Xpp (estable/volátil)
- Margen operativo: tendencia [creciente/estable/decreciente]

**Durabilidad**: [Alta/Media/Baja] — ¿puede mantenerse 10+ años? ¿Qué lo amenaza?
```

## Búsqueda web complementaria

Cuando sea relevante, busca información competitiva actualizada:
- Nuevos competidores entrando al mercado
- Cambios tecnológicos que puedan erosionar el moat
- Movimientos regulatorios recientes
- Market share reciente si disponible públicamente
