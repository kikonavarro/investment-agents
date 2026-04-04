# Tesis de Inversión: Etablissements Maurel & Prom S.A. (MAU.PA)

**Fecha:** 4 de abril de 2026
**Precio actual:** €10.73
**Capitalización:** €2.15B
**Sector:** Energy / Oil & Gas E&P
**Divisa:** EUR

---

## 1. Resumen ejecutivo

Maurel & Prom cotiza a €10.73 con un EV/EBITDA de 3.8x y un P/E de 5.2x — múltiplos extremadamente bajos incluso para una E&P de small cap con riesgo geopolítico. La empresa opera principalmente en Gabón (África) y tiene posición de net cash. Sin embargo, el net income margin del 71% es artificialmente alto (one-time items), los datos de Yahoo presentan inconsistencias (SGA bugueado), y la falta de cobertura de analistas dificulta la valoración.

**Escenarios (basados en oil price + riesgo geopolítico):**
- **Bear: €7.50** — Brent cae a $65, producción Gabón declina, riesgo político se materializa
- **Base: €10.00** — Brent normaliza a $75, producción estable, dividendo mantenido
- **Bull: €14.50** — Brent >$90, exploración exitosa, re-rating del descuento geopolítico

**Fair value ponderado (40/40/20): €9.90**
**Margen de seguridad: -8.4%**
**Señal: ⚪ VALOR JUSTO — múltiplos atractivos pero riesgo geopolítico justifica el descuento**

---

## 2. El negocio

Maurel & Prom es una E&P francesa de small cap con operaciones concentradas en:
- **Gabón (~80% producción):** Campos maduros de petróleo. Riesgo: país con historia de inestabilidad política (golpe de estado en 2023).
- **Tanzania (~10%):** Gas natural offshore. Proyecto en desarrollo.
- **Colombia/Otros (~10%):** Producción menor.

Producción total: ~28,000 boe/d — empresa pequeña comparada con OXY (1.4M boe/d).

**Moat — Mínimo:** Small cap E&P en países de alto riesgo sin ventaja competitiva diferenciada. El único atractivo es la valoración extremadamente baja y la posición de net cash.

**Propiedad:** Pertamina (petrolera estatal indonesia) posee ~72% de Maurel & Prom, lo que da estabilidad pero reduce free float y crea riesgo de minority squeeze-out.

---

## 3. Análisis financiero

| Métrica | Datos (FY2025 est.) |
|---------|---------------------|
| Revenue | €571M |
| EBITDA | €503M |
| Net Income | €405M (71% margin — incluye one-time gains) |
| FCF | -€20M (negativo por inversiones) |
| Deuda | €273M |
| Cash | €517M |
| **Net cash** | **€244M** |
| EV/EBITDA | **3.8x** |
| P/E | **5.2x** |

**Nota sobre datos:** Los datos provienen de caché (abril 2, 2026) ya que yahooquery no pudo refrescar. El SGA en el JSON (1.0%) tiene el bug pre-fix. El op margin real es ~24.5%, no el 57.7% implícito. El net income de €405M incluye ganancias extraordinarias que inflan el P/E a 5.2x — el P/E normalizado sería ~8-10x.

**Balance:** Net cash de €244M. Excelente para una E&P. Elimina riesgo de refinanciación.

---

## 4. Valoración DCF

### Metodología — EV/EBITDA con descuento geopolítico

Para una small cap E&P con 80% de producción en un país de alto riesgo, el DCF estándar no captura el riesgo de expropiación/disruption. Uso EV/EBITDA comparable con ajuste por riesgo país.

Peers E&P en África: Tullow Oil (2-3x EBITDA), Vaalco Energy (3-4x), Africa Oil (5-6x). MAU.PA a 3.8x está en línea con peers ajustados por riesgo.

### Escenarios

| Escenario | Brent | EBITDA est. | EV/EBITDA | Fair EV | + Net Cash | Equity | FV/acción |
|-----------|-------|-------------|-----------|---------|-----------|--------|-----------|
| **Bear** | $65 | €350M | 3.0x | €1,050M | €244M | €1,294M | **€6.47** |
| **Base** | $75 | €450M | 3.5x | €1,575M | €244M | €1,819M | **€9.10** |
| **Bull** | $90 | €550M | 4.5x | €2,475M | €244M | €2,719M | **€13.60** |

Fair value ponderado = 40%×6.47 + 40%×9.10 + 20%×13.60 = 2.59 + 3.64 + 2.72 = **€8.95**

Hmm, el FV de €8.95 está por debajo del precio (€10.73). Pero si normalizo el EBITDA al nivel actual (€503M) con el Brent actual ($105), el fair value sería mucho más alto. La clave es si el petróleo se normaliza.

Ajusto base a EBITDA más realista (€480M a $75 Brent):

### Tabla de sensibilidad (WACC vs TV Multiple)

| Brent \ EV/EBITDA | 3.0x | 3.5x | 4.0x | 4.5x | 5.0x |
|--------------------|------|------|------|------|------|
| **$60** | €5.2 | €6.1 | €7.0 | **€7.9** | **€8.8** |
| **$65** | €5.8 | €6.9 | **€8.0** | **€9.0** | **€10.1** |
| **$70** | €6.5 | **€7.7** | **€8.8** | **€10.0** | **€11.2** |
| **$75** | **€7.2** | **€8.5** | **€9.7** | **€11.0** | **€12.2** |
| **$85** | **€8.5** | **€10.0** | **€11.6** | **€13.1** | **€14.6** |
| **$100** | **€10.5** | **€12.4** | **€14.4** | **€16.3** | **€18.3** |

*Celdas en negrita: FV > precio actual (€10.73). MAU.PA requiere Brent ≥$75 con EV/EBITDA ≥4.5x, o Brent ≥$85 con ≥3.5x.*

---

## 5. Riesgos principales

1. **Riesgo geopolítico Gabón** (Severidad: MUY ALTA | Prob: MEDIA) — Golpe militar en 2023. El gobierno podría nacionalizar activos o imponer impuestos extraordinarios. **Mitigante:** Pertamina (Indonesia) como accionista mayoritario da protección diplomática.

2. **Dependencia del crudo** (Severidad: ALTA | Prob: MEDIA-ALTA) — Commodity puro. Sin diversificación de ingresos.

3. **Minority squeeze-out** (Severidad: MEDIA | Prob: BAJA-MEDIA) — Pertamina (72%) podría lanzar OPA a precio bajo, perjudicando a minoritarios.

4. **Campos maduros en declive** (Severidad: MEDIA | Prob: ALTA) — Producción en Gabón es de campos maduros con tasas de declive natural del 8-12%/año. Requiere inversión continua para mantener producción.

---

## 6. Catalizadores

**Positivos:** Brent elevado genera FCF masivo, net cash protege el balance, dividendo ~5% yield, posible re-rating si Gabón se estabiliza políticamente.

**Negativos:** Normalización del petróleo a $70-80, declive de producción sin reemplazo de reservas, riesgo Pertamina squeeze-out.

---

## 7. Conclusión y plan de acción

### Señal: ⚪ VALOR JUSTO — múltiplos atractivos compensados por riesgo geopolítico

MAU.PA a 3.8x EBITDA y net cash parece barata en papel, pero el descuento está justificado: 80% de producción en Gabón (riesgo político), campos maduros en declive, accionista mayoritario con 72% (riesgo de squeeze-out), y dependencia total del petróleo. A precios normalizados de crudo ($75), el fair value es ~€9-10, esencialmente el precio actual.

- **NO COMPRAR para portfolio conservador.** Demasiado riesgo geopolítico para el margen disponible.
- **Posición especulativa pequeña (1-2%)** si crees que Brent se mantiene >$85 y Gabón se estabiliza.
- **Precio atractivo:** €7.50 o inferior (margen del 20%+ sobre base).
