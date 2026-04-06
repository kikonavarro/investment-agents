# Tesis de Inversión: NVIDIA Corporation (NVDA)

**Fecha:** 6 de abril de 2026
**Precio actual:** $176.15
**Market Cap:** $4.28T | **EV/EBITDA:** 29.3x | **P/E (TTM):** 35.7x

---

## Resumen ejecutivo

NVIDIA es la empresa más importante del ecosistema de inteligencia artificial. Domina el mercado de aceleradores AI con ~80-85% de cuota, genera márgenes brutos del 71% en hardware (sin precedentes en semiconductores) y ha multiplicado sus ingresos por 8 en tres años. Sin embargo, desde una perspectiva de value investing, el precio actual descuenta un nivel de crecimiento futuro que deja poco margen de seguridad.

- **Bear:** $105/acción — desaceleración del ciclo de capex AI, compresión de márgenes por competencia ASIC
- **Base:** $168/acción — crecimiento robusto con desaceleración gradual, márgenes estables
- **Bull:** $218/acción — AI como infraestructura permanente, NVDA mantiene dominio y pricing power

**Fair value ponderado (40/40/20):** $153
**Margen de seguridad:** -15.1%
**Señal:** 🟠 LIGERAMENTE SOBREVALORADA — gran empresa, precio exigente. Esperar corrección para entrada con margen de seguridad.

---

## 1. El negocio

### Qué hace NVIDIA

NVIDIA diseña y vende GPUs y plataformas de computación acelerada. Opera en dos segmentos reportados:

| Segmento | FY2026 Revenue | % Total | Descripción |
|----------|---------------|---------|-------------|
| Compute & Networking | ~$196B | ~91% | Data Center (GPUs AI, DGX, networking), Automotive |
| Graphics | ~$20B | ~9% | Gaming (GeForce), Professional Visualization (Quadro/RTX) |

Dentro de Compute & Networking, **Data Center** domina con ~$194B en FY2026 (+68% YoY), impulsado por la demanda de entrenamiento e inferencia de modelos de inteligencia artificial. Los clientes principales son hyperscalers (Amazon, Google, Microsoft, Meta, Oracle) y sovereign AI initiatives.

### Modelo de negocio

NVIDIA opera un modelo de **plataforma de hardware + software**:

1. **Hardware** (GPUs, sistemas DGX, networking): ciclo de producto anual (Hopper → Blackwell → Rubin). Cada generación ofrece saltos de rendimiento de 2-4x, forzando upgrades.
2. **Software/Ecosistema (CUDA)**: 20+ años de desarrollo, 4M+ desarrolladores, bibliotecas optimizadas (cuDNN, TensorRT, NCCL). CUDA es el verdadero moat — migrar a otra plataforma requiere reescribir código y reentrenar equipos.
3. **Networking (Mellanox/Spectrum-X)**: interconexión de alta velocidad entre GPUs, cada vez más crítica para clusters de miles de GPUs.

**Unit economics excepcionales**: GM del 71.1% en hardware gracias al pricing power de monopolio. Un rack de Blackwell GB200 NVL72 cuesta ~$3M, y los hyperscalers compran decenas de miles. El coste de fabricación (TSMC foundry + HBM3E) es ~25-30% del precio de venta.

### Pricing power y escalabilidad

NVDA puede subir precios generación tras generación porque:
- No hay alternativa viable para training de modelos frontier
- El coste de GPU es <5% del coste total de un data center (energía, cooling, red, edificio)
- El ROI del AI compute es masivo para los clientes (eficiencia, nuevos productos, ingresos publicitarios)

---

## 2. Moat — Wide Moat (Morningstar 5/5)

| Fuente de moat | Rating | Justificación |
|----------------|--------|---------------|
| **Costes de cambio** | ⬛⬛⬛⬛⬛ | CUDA lock-in: 20 años de código, bibliotecas, herramientas. Migrar a ROCm (AMD) o oneAPI (Intel) requiere meses de reescritura y testing |
| **Activos intangibles** | ⬛⬛⬛⬛⬛ | IP en arquitectura GPU, NVLink, CUDA. >20,000 patentes. Liderazgo técnico de ~2 generaciones sobre competencia |
| **Efecto red** | ⬛⬛⬛⬛⬜ | Más desarrolladores → más software optimizado → más usuarios → más desarrolladores. 4M+ devs en CUDA vs ~200K en ROCm |
| **Ventaja de escala** | ⬛⬛⬛⬛⬜ | Mayor cliente de TSMC → acceso prioritario a CoWoS packaging y nodos avanzados. Escala de I+D ($32.4B en FY2026) inigualable |
| **Ventaja de coste** | ⬛⬛⬛⬜⬜ | No tiene ventaja de coste per se (fabless), pero la escala permite amortizar I+D sobre base masiva de ingresos |

**Rating: Wide Moat.** El ecosistema CUDA es comparable al moat de Windows/Office de Microsoft en los 2000s. La diferencia es que los hyperscalers están activamente buscando alternativas (custom ASICs), lo que podría erosionar el moat en 5-10 años.

---

## 3. Análisis financiero

### Evolución histórica

| Métrica | FY2023 | FY2024 | FY2025 | FY2026 |
|---------|--------|--------|--------|--------|
| Revenue ($B) | 26.97 | 60.92 | 130.50 | 215.94 |
| YoY Growth | -10.6%¹ | +126% | +114% | +65% |
| EBITDA ($B) | 5.99 | 35.58 | 86.14 | 144.55 |
| Net Income ($B) | 4.37 | 29.76 | 72.88 | 120.07 |
| FCF ($B) | 3.81 | 27.02 | 60.85 | 96.68 |
| Gross Margin | 56.9% | 72.7% | 75.0% | 71.1% |
| Net Margin | 16.2% | 48.8% | 55.8% | 55.6% |

¹ FY2023 fue el valle post-crypto/gaming antes de la explosión AI.

**Nota importante**: El salto de 126% en FY2024 fue crecimiento 100% orgánico por la revolución AI, NO una adquisición (a pesar de la detección automática del sistema). La adquisición de Mellanox fue en 2020 y ya estaba integrada.

### Tendencia de márgenes

Gross margin cayó de 75% (FY2025) a 71.1% (FY2026) por costes de ramp-up de Blackwell, pero se recuperó trimestre a trimestre: Q1 71.3% → Q2 72.7% → Q3 73.6% → Q4 75.2%. Los márgenes están normalizándose en la zona 73-75% a medida que Blackwell escala.

### Balance

- **Total Debt:** $11.4B | **Cash + inversiones:** $62.6B | **Net Cash:** $51.1B
- **D/E Ratio:** prácticamente 0 — balance impecable
- No necesita financiación externa. Genera ~$97B de FCF anual

### Capital allocation

| Métrica | FY2026 |
|---------|--------|
| FCF | $96.7B |
| Buybacks | ~$34B (estimado) |
| Dividendos | ~$1B |
| CapEx | ~$5.6B (2.6% revenue) |
| ROIC | >80% |

NVDA prioriza: (1) reinversión en I+D ($32.4B, 15% revenue), (2) buybacks agresivos, (3) dividendo simbólico. ROIC extraordinario dado el modelo fabless — capex mínimo, casi todo el beneficio es cash. La recompra de acciones es coherente con la generación de caja.

---

## 4. Valoración DCF

### Parámetros (decididos con criterio, NO auto-generados)

**WACC:**
- Re (CAPM) = 4% + 2.335 × 5.5% = 16.8%. Sin embargo, la volatilidad del stock (beta 2.33) sobreestima el riesgo de negocio de un monopolio con 71% GM y net cash. Ajusto a 10% (base) por calidad de negocio, +1pp bear, -0.5pp bull.
- Deuda insignificante → WACC ≈ Ke

**TV Multiple (EV/EBITDA):**
- NVDA cotiza a 29.3x hoy. En Y5, con crecimiento desacelerando, el múltiplo debería comprimir. Uso 20x (bear), 22x (base), 25x (bull) — premium justificado por moat y margen.

**Nota sobre crecimiento**: Q1 FY2027 guidance de $78B implica ~40% YoY growth para el trimestre. Los hyperscalers han comprometido $660-700B en capex 2026. La visibilidad a 1-2 años es alta; a 3-5 años, la incertidumbre sobre el ciclo AI aumenta significativamente.

### Escenarios

| Parámetro | Bear | Base | Bull |
|-----------|------|------|------|
| Revenue Growth Y1 | +28% | +38% | +40% |
| Revenue Growth Y2 | +15% | +20% | +22% |
| Revenue Growth Y3 | +8% | +12% | +15% |
| Revenue Growth Y4 | +3% | +8% | +10% |
| Revenue Growth Y5 | +1% | +5% | +7% |
| Gross Margin | 66% | 71% | 72% |
| SGA % | 5.0% | 4.5% | 4.0% |
| R&D % | 16.0% | 15.0% | 14.0% |
| D&A % | 2.7% | 2.7% | 2.7% |
| CapEx % | 3.0% | 2.6% | 2.5% |
| Tax Rate | 12% | 11.4% | 11% |
| WACC | 11% | 10% | 9.5% |
| TV Multiple (EV/EBITDA) | 20x | 22x | 25x |

**Narrativa por escenario:**

- **Bear**: El ciclo de capex AI se desacelera en 2027-2028. Hyperscalers reducen inversión ante presión de márgenes y ROI decreciente. Custom ASICs (Google TPU, Amazon Trainium3) capturan 30%+ del mercado de inferencia. Restricciones China se endurecen. GM comprime a 66% por competencia de AMD y presión de precios.

- **Base**: La adopción de AI continúa pero se normaliza. NVDA mantiene ~70-75% de cuota en training, pierde share gradualmente en inferencia. Rubin (2026) y Rubin Ultra (2027) sostienen el ciclo de upgrade. Márgenes estables gracias a pricing power en training. China sigue bloqueada pero compensada por demanda global y sovereign AI.

- **Bull**: AI se convierte en infraestructura permanente como el cloud. NVDA mantiene >75% de cuota gracias a CUDA y cadencia anual de productos. Robotics (Omniverse, Isaac) y automotive contribuyen $10B+ adicionales. Márgenes expanden con escala y eficiencia de Rubin.

### Proyección de Revenue ($B)

| Año | Bear | Base | Bull |
|-----|------|------|------|
| Base (FY2026) | 215.9 | 215.9 | 215.9 |
| Y1 (FY2027) | 276.4 | 298.0 | 302.3 |
| Y2 (FY2028) | 317.9 | 357.6 | 368.8 |
| Y3 (FY2029) | 343.3 | 400.5 | 424.1 |
| Y4 (FY2030) | 353.6 | 432.5 | 466.6 |
| Y5 (FY2031) | 357.1 | 454.2 | 499.2 |

### Resultado DCF

| Métrica | Bear | Base | Bull |
|---------|------|------|------|
| EBITDA Y5 ($B) | 170.3 | 246.2 | 283.1 |
| UFCF Y5 ($B) | 140.3 | 207.7 | 240.9 |
| PV(UFCFs) ($B) | 472.7 | 660.7 | 747.3 |
| Terminal Value ($B) | 3,407.0 | 5,415.5 | 7,076.5 |
| PV(TV) ($B) | 2,022.4 | 3,362.6 | 4,495.8 |
| Enterprise Value ($B) | 2,495.1 | 4,023.3 | 5,243.1 |
| + Net Cash ($B) | 51.1 | 51.1 | 51.1 |
| Equity Value ($B) | 2,546.2 | 4,074.4 | 5,294.3 |
| **Fair Value/acción** | **$105** | **$168** | **$218** |
| vs Precio actual | -40.4% | -4.6% | +23.8% |
| TV como % del EV | 81.1% | 83.6% | 85.7% |

| Escenario | Fair Value | vs Precio |
|-----------|------------|-----------|
| Bear | **$105** | -40.4% |
| Base | **$168** | -4.6% |
| Bull | **$218** | +23.8% |

**Fair Value Ponderado:** 40% × $105 + 40% × $168 + 20% × $218 = **$153**
**Margen de seguridad:** ($153 - $176.15) / $153 = **-15.1%**

### Validación Gordon Growth (base)

TV_Gordon = UFCF_Y5 × (1 + g) / (WACC - g) = $207.7B × 1.025 / 0.075 = $2,838B
vs TV_Exit = $246.2B × 22 = $5,416B

El Exit Multiple da 1.9x más que Gordon Growth. Fair value con Gordon: ~$102/acción. Esto confirma que el TV múltiple de 22x es generoso — el rango realista está entre $102 (Gordon) y $168 (Exit Multiple). **La media de ambos métodos sugiere ~$135/acción**, reforzando la conclusión de sobrevaloración moderada.

### Tabla de sensibilidad — Fair Value por acción (escenario base)

| WACC \ TV | 18x | 20x | 22x | 24x | 26x |
|-----------|-----|-----|-----|-----|-----|
| **9.0%** | $149 | $162 | $175 | $188 | $201 |
| **9.5%** | $146 | $158 | $171 | $184 | $197 |
| **10.0%** | $142 | $155 | **$168** | $180 | $193 |
| **10.5%** | $140 | $152 | $164 | **$177** | $189 |
| **11.0%** | $137 | $149 | $161 | $173 | $185 |

Precio actual: $176.15. Para justificarlo se necesita: WACC 10% con TV 24x, o WACC 10.5% con TV 24x, o WACC 9% con TV 22x. El mercado está descontando la combinación más optimista del rango razonable.

### Análisis de impacto (sensibilidad a variables clave)

| Variable | Cambio | Impacto en FV (base) | Comentario |
|----------|--------|---------------------|------------|
| TV Multiple | +1x | +$6-7/acción | Variable más impactante después de GM |
| Gross Margin | +1pp | +$8-10/acción | La variable que más mueve la aguja |
| WACC | +50bps | -$3-4/acción | Impacto moderado |
| Revenue Growth Y1 | +1pp | +$2-3/acción | Efecto acumulativo en todos los años |

**La variable más crítica es el gross margin.** Si NVDA mantiene 73-75% (como sugiere Q4 FY2026), el fair value base sube a $175-185, justificando el precio actual. Si la competencia de ASICs presiona márgenes a 65-66%, el fair value cae a $100-110.

### Sanity checks

| Check | Resultado | Status |
|-------|-----------|--------|
| Bear vs Precio | -40% (bear = $105 vs $176) | ⚠️ Bear significativamente debajo — refleja riesgo real de ciclo AI |
| Bull/Bear ratio | 2.08x | ⚠️ Ligeramente por encima de 2.0x — reflejo de la incertidumbre extrema |
| TV como % del EV | 81-86% | ⚠️ Alto pero esperado en growth. Gordon Growth valida como ~$102 |
| P/E implícito (base) | 33.9x | ✅ Coherente con PEG ~1x para 37% growth |
| Growth base Y1 (38%) vs CAGR | Muy por debajo del CAGR 3Y (100%+) | ✅ Conservador vs histórico |
| vs Consenso analistas | $153 vs $268 media | ⚠️ Nuestro FV es 43% debajo del consenso — somos más conservadores, coherente con value investing |

---

## 5. Riesgos principales

| # | Riesgo | Severidad | Probabilidad | Impacto en tesis |
|---|--------|-----------|-------------|-----------------|
| 1 | **Desaceleración del ciclo AI capex** | 🔴 Alta | 🟡 Media | Si hyperscalers recortan capex 30-40%, NVDA pierde $60-80B de revenue. El timing es impredecible |
| 2 | **Custom ASICs (Google TPU, Amazon Trainium)** | 🟠 Alta | 🟠 Alta | Shipments de ASICs crecen 44.6% vs 16.1% GPUs. A 5 años, NVDA podría perder 20-30% de share en inferencia |
| 3 | **Concentración de clientes** | 🟠 Alta | 🟡 Media | Top 4 hyperscalers representan >60% de Data Center revenue. Si uno insourcea (como Google), impacto material |
| 4 | **Restricciones China** | 🟡 Media | 🟠 Alta | Mercado de $50B inaccesible. NVDA ya guía $0 de China en Q1 FY2027. Impacto absorbido pero limita TAM |
| 5 | **Compresión de márgenes** | 🟠 Alta | 🟡 Media | Si AMD/Intel fuerzan competencia en inferencia, GM podría caer de 71% a 65%. Cada 1pp = -$8-10 FV |

### Riesgo macro: aranceles y guerra comercial

La actual escalada de tensiones comerciales EEUU-China representa un riesgo adicional. Restricciones más amplias a exportaciones de semiconductores o represalias contra la cadena de suministro (TSMC en Taiwán) podrían disrumpir la producción. NVDA depende al 100% de TSMC para fabricación.

---

## 6. Catalizadores

### Positivos (12-24 meses)
- **Rubin GPU (H2 2026)**: nueva generación con 3.6x rendimiento vs Blackwell. Ciclo de upgrade masivo
- **Sovereign AI**: gobiernos construyendo infraestructura AI nacional (Arabia Saudí, UAE, India, Europa)
- **Reapertura parcial de China**: si EEUU relaja restricciones, $5-10B+ de upside inmediato
- **Automotive/Robotics**: segmentos incipientes que podrían contribuir $10B+ a medio plazo
- **Márgenes brutos >73%**: si Q1-Q2 FY2027 confirman normalización a 73-75%, el base case mejora

### Negativos (12-24 meses)
- **Exceso de capacidad GPU**: a medida que supply catches up, el pricing power de NVDA podría erosionarse
- **Capex fatigue**: si hyperscalers no ven ROI claro del AI spend, recortan presupuestos
- **Antitrust**: un dominio de >80% de mercado atrae escrutinio regulatorio
- **Trainium3 de Amazon**: chip 3nm con performance competitiva. Si AWS migra workloads internamente, pierde su mayor cliente

---

## 7. Conclusión y plan de acción

### Veredicto

NVIDIA es, probablemente, la mejor empresa de semiconductores que ha existido jamás. Ha construido un monopolio natural en AI compute con márgenes de software en un negocio de hardware. El ecosistema CUDA es un moat comparable al de Windows en los 90s.

**Sin embargo, como value investors, no compramos empresas — compramos a precios.** A $176.15, el mercado descuenta un escenario cercano al bull case: crecimiento sostenido >20% anual durante 5 años con márgenes estables y múltiplo terminal premium. Nuestro DCF muestra que el fair value ponderado ($153) está un 15% por debajo del precio actual. Incluso nuestro caso base ($168) queda ligeramente por debajo.

La tabla de sensibilidad revela que para justificar $176 necesitas combinar WACC ≤10% con TV ≥24x. Esto no es imposible — NVDA podría merecerlo si mantiene márgenes de 73-75% y el ciclo AI se extiende — pero no ofrece margen de seguridad para un inversor prudente.

### Señal: 🟠 LIGERAMENTE SOBREVALORADA

### Plan de acción

1. **NO comprar a precios actuales.** Sin margen de seguridad
2. **Zona de interés:** $130-140 (15-25% de descuento sobre FV base). A esos precios hay margen de seguridad razonable
3. **Watchlist activa:** monitorizar:
   - Márgenes brutos trimestrales (si se mantienen >73%, nuestro FV base sube a ~$175-185)
   - Capex de hyperscalers (si recortan, el bear se activa)
   - Cuota de mercado de ASICs (la mayor amenaza a largo plazo)
4. **Tamaño de posición si se alcanza zona de entrada:** 3-5% del portfolio. Calidad excepcional pero concentración sectorial alta
5. **Revisión en próximos earnings** (Q1 FY2027, ~mayo 2026): si guidance >$80B y GM >74%, reconsiderar FV

---

*Fuentes: NVIDIA 10-K FY2026 (SEC EDGAR), NVIDIA Q4 FY2026 Earnings Release, Yahoo Finance, analyst consensus (MarketBeat/TipRanks), CNBC, Motley Fool, Futurum Group, Tom's Hardware.*
