---
name: risk-analyst
description: >
  Análisis de riesgos materiales de empresas para inversión. Usa esta skill
  cuando necesites evaluar los riesgos de una empresa, su perfil de riesgo,
  o amenazas a la tesis de inversión. Se ejecuta SIEMPRE como parte de
  cualquier tesis de inversión. También se puede invocar de forma independiente
  con "riesgos de X", "qué riesgos tiene X", "análisis de riesgo de X".
---

# Risk Analyst — Análisis de Riesgos Materiales

## Principio fundamental

> "El riesgo viene de no saber lo que estás haciendo." — Warren Buffett

El objetivo NO es listar todos los riesgos posibles. Es identificar los 4-5 riesgos
que realmente podrían destruir la tesis de inversión, priorizados por impacto × probabilidad.

## Paso 0: Obtener los datos

Si no existe `data/valuations/{TICKER}/{TICKER}_valuation.json`:
```bash
python main.py --analyst TICKER --data-only
```

Lee el JSON. Necesitas: business_summary, sector, industry, country, latest_financials
(deuda, cash, márgenes), historical_data (tendencias), segments (concentración), news.

## Categorías de riesgo (evaluar TODAS)

### 1. Riesgo de concentración
- **Clientes**: ¿Top 1-3 clientes representan >30% del revenue? → riesgo alto
- **Proveedores**: ¿Dependencia de pocos proveedores? ¿Hay alternativas?
- **Geografía**: ¿Revenue concentrado en 1 país/región? Riesgo geopolítico
- **Segmentos**: ¿Un segmento domina >70% del revenue? → negocio no diversificado
- **Fuente**: Revisar `segments` del JSON para concentración de revenue

### 2. Riesgo financiero
- **Apalancamiento**: Debt/Equity, Debt/EBITDA, Interest Coverage
  - Debt/EBITDA > 3x → precaución
  - Debt/EBITDA > 5x → peligro
  - Interest coverage < 3x → riesgo de default
- **Liquidez**: Current ratio, Quick ratio, Cash vs obligaciones a corto plazo
- **Vencimientos de deuda**: ¿Hay refinanciaciones próximas? ¿En entorno de tipos altos?
- **Dilución**: ¿Stock-based compensation significativa? SBC/FCF > 20% → problema
- **Calcular desde** `latest_financials`: total_debt, cash, total_equity, ebitda

### 3. Riesgo regulatorio
- **Cambios legislativos**: ¿Sector bajo escrutinio? (tech, energía, farma, financiero)
- **Antimonopolio**: ¿Cuota de mercado dominante que atraiga reguladores?
- **Licencias**: ¿Depende de licencias renovables? ¿Riesgo de no renovación?
- **ESG/Medioambiental**: ¿Pasivos medioambientales potenciales?
- **Geopolítico**: ¿Operaciones en países con riesgo político? Sanciones, aranceles

### 4. Riesgo competitivo
- **Disrupción tecnológica**: ¿IA, automatización, nueva tecnología amenaza el negocio?
- **Nuevos entrantes**: ¿Barreras de entrada suficientes? (ver moat-analyst)
- **Commoditización**: ¿El producto se está volviendo commodity? Señal: márgenes decrecientes
- **Sustitutos**: ¿Hay productos/servicios que reemplacen lo que ofrece?

### 5. Riesgo macro
- **Ciclicidad**: ¿Revenue correlacionado con ciclo económico?
  - Calcular: varianza de revenue en histórico. Si caída >15% en algún año → cíclica
- **Tipos de interés**: ¿Empresa sensible a tipos? (inmobiliario, utilities, alto apalancamiento)
- **Divisa**: ¿Revenue en múltiples divisas? ¿Hedging natural?
- **Inflación**: ¿Puede trasladar costes al cliente? (pricing power)

### 6. Riesgo operacional
- **Dependencia de personas clave**: CEO fundador, talento técnico escaso
- **Cadena de suministro**: ¿Vulnerabilidades conocidas? Post-COVID lessons
- **Ciberseguridad**: ¿Maneja datos sensibles? ¿Sector objetivo de ataques?
- **Ejecución**: ¿Transición de estrategia en curso? ¿Integración de M&A?

### 7. Riesgo de valoración
- **Precio ya incluye perfección**: Si el bear case del DCF da downside >30%, el mercado
  puede estar asumiendo que todo sale bien
- **Sensibilidad del DCF**: ¿Qué variable mueve más el precio? Ese es tu riesgo principal
- **Reversión a la media**: ¿Márgenes muy por encima del sector? Pueden revertir

## Matriz de riesgo: Severidad × Probabilidad

Para cada riesgo identificado, evalúa:

| | Probabilidad Baja | Probabilidad Media | Probabilidad Alta |
|---|---|---|---|
| **Severidad Alta** | Monitorear | Riesgo MATERIAL | Riesgo CRÍTICO |
| **Severidad Media** | Aceptable | Monitorear | Riesgo MATERIAL |
| **Severidad Baja** | Ignorar | Aceptable | Monitorear |

Solo los riesgos MATERIAL y CRÍTICO entran en el top 4-5.

## Mitigantes

Para cada riesgo material, identifica:
1. **Mitigantes internos**: ¿Qué hace la empresa para mitigarlo? (diversificación, hedging, reservas)
2. **Mitigantes externos**: ¿Qué factores naturales limitan el riesgo?
3. **Capacidad de respuesta**: ¿La empresa ha gestionado bien crisis pasadas?

## Estructura del output

```markdown
### Riesgos principales

| # | Riesgo | Categoría | Severidad | Probabilidad | Impacto en tesis |
|---|--------|-----------|-----------|--------------|------------------|
| 1 | [descripción concreta] | Financiero/Regulatorio/etc. | Alta/Media | Alta/Media | [cómo afecta] |
| 2 | ... | ... | ... | ... | ... |
| 3 | ... | ... | ... | ... | ... |
| 4 | ... | ... | ... | ... | ... |

**Riesgo #1: [Nombre]**
- Descripción: [2-3 frases con datos concretos]
- Escenario adverso: [Qué pasaría si se materializa]
- Mitigantes: [Qué lo compensa]
- Monitoreo: [Qué vigilar para detectarlo a tiempo]

[Repetir para cada riesgo]

**Riesgo de valoración**: [1-2 frases sobre qué asume el mercado y dónde puede fallar]

**Perfil de riesgo global**: [Bajo/Moderado/Alto] — [1 frase justificativa]
```

## Reglas inquebrantables

1. **No listas genéricas** — "riesgo de recesión" sin contexto no vale. Cuantifica cómo afecta a ESTA empresa
2. **Máximo 5 riesgos** — si tienes 10, no has priorizado bien. Filtra por materialidad
3. **Datos concretos** — "deuda alta" no vale. "Debt/EBITDA de 4.2x con vencimientos en 2026" sí
4. **Mitigantes siempre** — un riesgo sin mitigante es alarmismo. Un mitigante sin riesgo es complacencia
5. **El riesgo de valoración siempre** — ¿qué pasa si tu DCF está equivocado?
