---
name: business-model
description: >
  Análisis de modelo de negocio de empresas. Usa esta skill cuando necesites
  entender cómo gana dinero una empresa, sus fuentes de ingresos, unit economics,
  escalabilidad, o dependencias. Se ejecuta SIEMPRE como parte de cualquier tesis
  de inversión. También se puede invocar de forma independiente con "modelo de
  negocio de X", "cómo gana dinero X", "unit economics de X".
---

# Business Model Analyst — Análisis de Modelo de Negocio

## Principio fundamental

> "Nunca inviertas en un negocio que no puedas entender." — Warren Buffett

Antes de valorar una empresa, tienes que entender CÓMO gana dinero, POR QUÉ los clientes
le pagan, y si ese modelo es SOSTENIBLE y ESCALABLE.

## Paso 0: Obtener los datos

Si no existe `data/valuations/{TICKER}/{TICKER}_valuation.json`:
```bash
python main.py --analyst TICKER --data-only
```

Lee el JSON. Necesitas: business_summary, sector, industry, segments (con revenues por año),
historical_data (revenue, márgenes por año), latest_financials.

## Análisis del modelo de negocio

### 1. Fuentes de ingresos

Desde `segments` del JSON, analiza:

- **Diversificación**: ¿Cuántos segmentos? ¿Cuánto aporta cada uno?
  - 1 segmento >80% → concentrado (mayor riesgo, pero puede ser fortaleza si es dominante)
  - 3+ segmentos equilibrados → diversificado
- **Tendencia por segmento**: ¿Cuáles crecen y cuáles decrecen? Calcular CAGR por segmento
- **Tipo de ingreso por segmento**:
  - Recurrente (suscripciones, contratos, mantenimiento) → más predecible, mayor múltiplo
  - Transaccional (ventas puntuales, proyectos) → menos predecible
  - Mixto → ¿qué porcentaje es recurrente?
- **Revenue quality**: recurrencia + visibilidad + pricing power = calidad del revenue

### 2. Pricing power

- ¿Puede subir precios sin perder clientes? Evidencia:
  - Margen bruto creciente en un entorno inflacionario → pricing power
  - Revenue crece más que volumen → subidas de precio absorbidas
  - Producto esencial vs discrecional → el esencial tiene más pricing power
- **Test ácido**: ¿Qué pasaría si sube precios un 10%? ¿Los clientes se van o se quedan?

### 3. Unit economics

Evalúa la rentabilidad unitaria del negocio:

- **Margen bruto**: ¿Alto (>50%) o bajo (<30%)? ¿Mejorando o deteriorándose?
  - Software/SaaS: 70-85% típico
  - Servicios: 30-50% típico
  - Manufactura: 20-40% típico
  - Retail: 25-40% típico
- **Margen operativo**: ¿Después de SGA y R&D, queda beneficio suficiente?
  - Calcular: Operating leverage = ΔOperating Income / ΔRevenue
  - Si >1 → operating leverage positivo (escalable)
- **Conversión de FCF**: FCF/Net Income
  - >100% → excelente (genera más cash del que reporta como beneficio)
  - 80-100% → bueno
  - <60% → preocupante (¿capex alto? ¿working capital consumiendo cash?)

### 4. Escalabilidad

- **Marginal economics**: ¿El coste de servir un cliente adicional es bajo?
  - Software: coste marginal ≈ 0 → muy escalable
  - Servicios: necesita más personas → poco escalable
  - Manufactura: necesita más capacidad → moderadamente escalable
- **Operating leverage histórico**: ¿Los márgenes mejoran cuando crece el revenue?
  Calcular desde historical_data:
  ```
  Si revenue creció 20% y operating income creció 30% → hay operating leverage
  Si ambos crecieron igual → sin leverage
  Si operating income creció menos → diseconomías de escala
  ```
- **Capex intensity**: CapEx/Revenue
  - <5% → asset-light (escalable)
  - 5-15% → normal
  - >15% → capital-intensive (menos escalable)

### 5. Dependencias y vulnerabilidades

- **Clientes**: ¿Concentración? Top 5 clientes como % del revenue
- **Proveedores**: ¿Dependencia de un proveedor clave? ¿Hay alternativas?
- **Geografía**: Revenue por región. ¿Diversificado globalmente o concentrado?
- **Tecnología**: ¿Depende de una plataforma/ecosistema? (ej: apps que dependen de App Store)
- **Regulación**: ¿Sector regulado? ¿Licencias necesarias?
- **Personas**: ¿El negocio depende de personas clave?

### 6. Posición en la cadena de valor

- ¿Dónde está la empresa en la cadena de valor de su industria?
- ¿Tiene poder de negociación con proveedores (upstream)?
- ¿Tiene poder de negociación con clientes (downstream)?
- ¿Riesgo de desintermediación? (competidores que vayan directo al cliente)

## Clasificación del modelo de negocio

| Tipo | Características | Múltiplo típico |
|------|----------------|-----------------|
| **Plataforma/Marketplace** | Network effects, revenue recurrente, asset-light | Alto (20-40x EBITDA) |
| **SaaS/Suscripción** | Revenue recurrente, márgenes altos, escalable | Alto (15-30x EBITDA) |
| **Franquicia/Licencias** | Asset-light, fee-based, escalable | Alto (15-25x EBITDA) |
| **Producto de marca** | Pricing power, márgenes altos, crecimiento moderado | Medio-alto (12-20x EBITDA) |
| **Servicios profesionales** | Poco escalable, dependiente de personas | Medio (8-15x EBITDA) |
| **Manufactura diferenciada** | Capex-intensive pero con moat | Medio (8-15x EBITDA) |
| **Commodity/Retail** | Márgenes bajos, competencia en precio | Bajo (5-10x EBITDA) |
| **Cíclica pesada** | Revenue volátil, capex alto | Bajo (4-8x EBITDA) |

## Estructura del output

```markdown
### El negocio

**Qué hace**: [1-2 frases claras, sin jerga]

**Cómo gana dinero**:
| Segmento | Revenue (último año) | % del total | CAGR 3-5 años | Tipo |
|----------|---------------------|-------------|---------------|------|
| [Seg 1] | $X.XB | XX% | +X.X% | Recurrente/Transaccional |
| [Seg 2] | $X.XB | XX% | +X.X% | ... |

**Calidad del revenue**: [Alta/Media/Baja] — [% recurrente, visibilidad, pricing power]

**Unit economics**:
- Margen bruto: X% (sector: ~X%) — [superior/en línea/inferior]
- Margen operativo: X% — tendencia [creciente/estable/decreciente]
- FCF conversion: X% — [excelente/bueno/preocupante]
- Operating leverage: [positivo/neutro/negativo]

**Escalabilidad**: [Alta/Media/Baja] — CapEx/Revenue X%, coste marginal [bajo/medio/alto]

**Dependencias clave**: [lista de las 2-3 más importantes]

**Tipo de modelo**: [Plataforma/SaaS/Manufactura/etc.] — justifica el múltiplo de valoración
```

## Reglas inquebrantables

1. **Entiende antes de valorar** — si no puedes explicar el negocio en 2 frases, no lo has entendido
2. **Datos del JSON, no inventados** — usa segments y historical_data reales
3. **Tendencias > snapshots** — un margen de 30% no dice nada. Un margen que pasó de 25% a 35% en 5 años dice mucho
4. **Compara con el sector** — un margen bruto del 40% es excelente en retail pero pobre en software
5. **Sin jerga innecesaria** — explica como si le hablaras a un inversor inteligente pero no especialista
