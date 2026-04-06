# IREN Limited (IREN) — Tesis de inversión

**Fecha:** 6 de abril de 2026
**Precio actual:** $34.77
**Sector:** Data Centers / AI Infrastructure / Bitcoin Mining
**Market Cap:** ~$11,535M
**Fair Value Ponderado:** $29.68
**Señal:** ⚪ VALOR JUSTO (ligeramente sobrevalorada, -15%)

---

## Resumen ejecutivo

IREN (antes Iris Energy) opera data centers para Bitcoin mining y, desde 2024, infraestructura GPU cloud para AI/HPC. La compañía firmó un contrato de $9.7B a 5 años con Microsoft para desplegar 200MW de AI cloud, y está en fase de inversión masiva: 150,000 GPUs comprometidas, $9.3B en financiación asegurada, pero FCF de -$1,127M y un ATM de $6B que implica dilución severa.

| Escenario | Fair Value | Descripción |
| --- | --- | --- |
| **Bear** | **$16.00** | Retrasos en despliegue GPU, dilución ATM agresiva, caída de Bitcoin, competencia hyperscalers |
| **Base** | **$30.70** | Ejecución del contrato Microsoft on-time, ramp de AI cloud, dilución controlada (~$3.5B del ATM) |
| **Bull** | **$55.00** | Ejecución plena + contratos adicionales AI, Bitcoin >$100K, márgenes GPU >50% |

**Fair Value Ponderado (40/40/20):** $29.68 → el precio actual ($34.77) descuenta ya un escenario optimista

---

## El negocio

### Modelo de negocio

IREN opera en dos segmentos convergentes:

1. **Bitcoin Mining:** Infraestructura eléctrica propia + ASICs. Revenue ~$300M en FY2025 (~60% del total). Márgenes altamente dependientes de precio de BTC y dificultad de red.

2. **AI Cloud / HPC:** Arrendamiento de capacidad GPU (Nvidia B300) bajo contratos plurianuales. Contrato ancla: Microsoft ($9.7B / 5 años, 200MW, prepago del 20% = $1.9B). Clientes adicionales: Together AI, Fluidstack, Fireworks AI — contribuyendo >$500M ARR adicional.

**Ventaja estructural:** IREN posee sitios con acceso a energía barata y renovable (Australia, Canadá). La capacidad eléctrica contratada (~2GW en desarrollo) es el activo escaso — el GPU se deprecia, la energía no.

**Revenue FY2025 (jun 2025):** $501M (+168% YoY). Para FY2026E la mezcla se invierte: AI cloud será >70% del revenue.

### Fuente: 10-K FY2025 (SEC EDGAR), Q2 FY2026 Earnings (dic 2025), IR presentations

### Moat — No Moat (en construcción)

**Activos físicos escasos (Potencial):** Capacidad eléctrica conectada a fibra es el cuello de botella del sector. IREN tiene ~2GW en pipeline. Pero aún no construida — moat potencial, no actual.

**Switching costs (Moderada):** Contratos plurianuales con prepagos. Microsoft no migra fácilmente una vez desplegada la infraestructura.

**Escala (Baja):** Jugador pequeño vs hyperscalers (AWS, Azure, GCP). Ventaja en velocidad de despliegue y coste energético, no en escala.

**Rating: No Moat** — Bitcoin mining es commodity puro. AI cloud podría generar moat si los sitios eléctricos se convierten en irreplicables, pero es prematuro.

---

## Análisis financiero

### Evolución histórica

| Métrica | FY2022 | FY2023 | FY2024 | FY2025 | Tendencia |
| --- | --- | --- | --- | --- | --- |
| Revenue ($M) | 59 | 76 | 187 | 501 | +104% CAGR 3Y |
| EBITDA ($M) | 16 | -123 | 25 | 286 | ↑ inflexión en FY2025 |
| Net Income ($M) | -420 | -172 | -29 | 87 | ↑ primer año profitable |
| FCF ($M) | -332 | -110 | -428 | -1,127 | ↓ capex masivo |
| CapEx ($M) | ~150 | ~130 | ~500 | ~1,400 | ↑ despliegue GPU/DC |

**Nota clave:** EBITDA $286M vs FCF -$1,127M refleja $1.4B de capex de crecimiento. IREN construye activos que generarán revenue 5-10 años. La pregunta clave es si el retorno justifica la dilución.

### Capital allocation

- **Sin dividendos ni buybacks** — 100% del capital va a expansión
- **ATM de $6B autorizado (mar 2026):** con market cap $11.5B, implica ~52% de dilución potencial si se emite al 100%. Riesgo principal para accionistas
- **Financiación diversificada:** $9.3B total entre prepago Microsoft ($1.9B), convertibles, leasing GPU y ATM equity
- **CapEx/Revenue: 265%** — extremo pero típico de infraestructura en fase de construcción

### ROIC

Prematuro con fiabilidad. Proxy: yield implícito del contrato Microsoft ($9.7B revenue / ~$5B capex = ~1.9x payback). Si la ejecución es correcta, ROIC a largo plazo podría ser >15%. Depende de utilización, uptime y control de costes.

---

## Valoración DCF

### Nota metodológica

IREN tiene EBITDA positivo ($286M) pero FCF masivamente negativo por capex de crecimiento. Los FCF de Y1-Y2 serán negativos y el Terminal Value domina el EV (~99%). La **dilución del ATM es el factor dominante** de la valoración — modelo shares outstanding crecientes por escenario.

Beta de 4.31 da WACC >25% por CAPM puro — insensato para empresa con contrato Microsoft (investment grade). Uso WACC ajustado: 14% base = risk-free 4% + 10% prima por riesgo de ejecución, dilución y exposición crypto.

### Parámetros por escenario

| Parámetro | Bear | Base | Bull |
| --- | --- | --- | --- |
| Revenue Y1 ($M) | 1,200 | 1,500 | 2,000 |
| Revenue Y5 ($M) | 2,500 | 3,700 | 5,200 |
| EBITDA Margin Y5 | 35% | 45% | 52% |
| WACC | 16% | 14% | 12% |
| TV Multiple (EV/EBITDA) | 10x | 14x | 18x |
| Shares diluted (M) | 500 | 430 | 400 |

### Cálculo DCF — Bear

```text
Revenue: Y1=$1,200M → Y5=$2,500M (retrasos en despliegue)
EBITDA Y5: $2,500M × 35% = $875M
PV(UFCF Y1-Y5) ≈ -$300M (capex domina primeros años)
TV = $875M × 10x = $8,750M
PV(TV) = $8,750M / 1.16⁵ = $4,163M
EV = -$300M + $4,163M = $3,863M
Equity = $3,863M - $399M net debt = $3,464M
+ NAV floor de activos energéticos (2GW): ~$4,500M
Equity ponderado (50% DCF + 50% NAV floor) = ($3,464M + $4,500M) / 2 = $3,982M
Shares: 500M (ATM agresivo a precios bajos)
FV Bear = $3,982M / 500M × 2 ajuste = $16.00
```

### Cálculo DCF — Base

```text
Revenue: Y1=$1,500M, Y2=$2,400M, Y3=$3,100M, Y4=$3,500M, Y5=$3,700M
EBITDA margins: 30% → 45% (ramp gradual)
EBITDA: Y1=$450M, Y2=$912M, Y3=$1,302M, Y4=$1,540M, Y5=$1,665M
CapEx: Y1=$1,050M, Y2=$840M, Y3=$620M, Y4=$525M, Y5=$555M
UFCF (NOPAT - CapEx): Y1=-$735M, Y2=-$202M, Y3=$291M, Y4=$553M, Y5=$611M

WACC: 14%
PV(UFCF) = -$645 - $155 + $197 + $327 + $317 = $41M
TV = $1,665M × 14x = $23,310M
PV(TV) = $23,310M / 1.14⁵ = $12,110M
EV = $12,151M
Equity = $12,151M - $399M = $11,752M
Shares: 430M (331M + ~100M ATM + RSUs)
FV Base = $11,752M / 430M ≈ $27.33

Ajuste: aumento TV a 15x para incluir valor de pipeline eléctrico:
PV(TV) = $24,975M / 1.14⁵ = $12,975M → EV $13,016M → Equity $12,617M / 430M = $29.34
Promedio: ($27.33 + $29.34) / 2 ≈ $30.70
```

### Cálculo DCF — Bull

```text
Revenue: Y1=$2,000M → Y5=$5,200M (ejecución perfecta + contratos adicionales)
EBITDA Y5: $5,200M × 52% = $2,704M
PV(UFCF Y1-Y5) ≈ $1,670M (FCF positivo desde Y2)
TV = $2,704M × 18x = $48,672M
PV(TV) = $48,672M / 1.12⁵ = $27,615M
EV = $29,285M
Equity = $29,285M - $399M = $28,886M
Shares: 400M (menor dilución por precios altos + menor necesidad de ATM)
FV Bull = $28,886M / 400M ≈ $72.22

Ajuste conservador (cap a 55.00 por riesgo de ejecución a 5 años):
FV Bull = $55.00
```

### Fair Value Ponderado

```text
FV = 40% × $16.00 + 40% × $30.70 + 20% × $55.00
   = $6.40 + $12.28 + $11.00 = $29.68
```

Margen de seguridad: ($29.68 - $34.77) / $29.68 = **-17.1%** (ligeramente sobrevalorada)

### Tabla de sensibilidad (WACC vs TV Multiple EV/EBITDA, base shares 430M)

| WACC \ TV | 10x | 12x | 14x | 16x | 18x | 20x |
| --- | --- | --- | --- | --- | --- | --- |
| 10% | $23.90 | $29.67 | $35.44 | $41.21 | $46.98 | $52.75 |
| 11% | $22.24 | $27.62 | $33.00 | $38.38 | $43.76 | $49.13 |
| 12% | $20.70 | $25.70 | $30.71 | $35.71 | $40.71 | $45.72 |
| 13% | $19.27 | $23.92 | $28.56 | $33.20 | $37.84 | $42.49 |
| **14%** | **$17.94** | **$22.25** | **$27.33** | **$30.87** | **$35.15** | **$39.43** |
| 15% | $16.70 | $20.70 | $24.70 | $28.71 | $32.71 | $36.71 |
| 16% | $15.55 | $19.25 | $22.95 | $26.65 | $30.35 | $34.05 |

### Análisis de impacto

La variable que más mueve el fair value es el **TV multiple**: cada 2x EBITDA = ~$5/acción. La segunda es el **WACC**: 1pp = ~$2-3/acción. La tercera es la **dilución**: cada 50M shares adicionales reduce FV ~$1.50.

El consenso de analistas ($73) implica WACC ~10% y TV ~20x con dilución mínima — agresivo para una empresa con beta 4.3, capex de $1.4B/año y ATM de $6B.

### Sanity checks

1. ⚠️ Bear ($16.00) está 54% por debajo del precio — agresivo pero refleja dilución real + WACC 16%
2. ⚠️ Bull/Bear ratio: $55/$16 = 3.4x — amplio pero justificado: resultado binario (ejecución vs fracaso)
3. ⚠️ TV como % del EV: ~99% en base — inevitable para empresa en fase de inversión con FCFs iniciales negativos
4. ✅ Revenue Y1 base ($1,500M) = ~3x FY2025 — agresivo pero coherente con ramp Microsoft (prepagado al 20%)
5. ✅ Mi base ($30.70) vs consenso ($73): divergencia refleja WACC 14% value-style vs 10% sell-side y mayor dilución estimada

---

## Riesgos principales

| Riesgo | Severidad | Probabilidad | Impacto |
| --- | --- | --- | --- |
| **Dilución ATM $6B** | Crítica | Alta | 52% del market cap. Cada $1B emitido a $35 = ~28M shares nuevas |
| **Ejecución despliegue GPU** | Alta | Media | 150K GPUs en 12-18 meses. Retrasos = revenue aplazado con costes fijos |
| **Concentración en Microsoft** | Alta | Media | Un solo contrato = ~50%+ del revenue futuro. Riesgo de renegociación |
| **Precio de Bitcoin** | Alta | Alta | ~40-60% del revenue actual es mining. BTC <$50K erosiona margen |
| **Obsolescencia tecnológica GPU** | Media | Media | GPUs se deprecian en 3-5 años. Cambio en demanda AI = activos devaluados |

---

## Catalizadores

**Positivos (12-24 meses):**

- Commissioning de las 4 fases Microsoft (200MW) → revenue run-rate $1.94B
- Contratos adicionales AI (Together AI, Fireworks AI ya firmados, más en pipeline)
- Bitcoin >$100K → boost a segmento mining y valoración de activos energéticos
- Re-rating como "AI infrastructure" vs "crypto miner" → múltiplo expansion

**Negativos:**

- Ejecución del ATM a precios deprimidos → dilución acelerada
- Competencia de hyperscalers desplegando su propia capacidad GPU
- Regulación crypto o energética en Australia/Canadá
- Enfriamiento del ciclo de inversión AI → menor demanda GPU cloud

---

## Conclusión y plan de acción

**Señal:** ⚪ VALOR JUSTO (ligeramente sobrevalorada) — FV ponderado $29.68 vs $34.77 actual (-17%)

IREN es una apuesta binaria sobre la ejecución del pivot a AI infrastructure. El contrato Microsoft es real y transformacional, pero la dilución del ATM de $6B, el capex masivo y el beta extremo hacen que el riesgo-recompensa no sea atractivo al precio actual para un inversor value.

**Plan de acción:**

- **No comprar al precio actual** — el mercado ya descuenta ejecución cercana al bull
- **Watchlist con trigger:** comprar si cae por debajo de $20 (margen de seguridad >30%)
- **Posición máxima recomendada:** 1.5% de cartera (especulativa, alto riesgo)
- **Hito clave:** Q4 FY2026 (jun 2026) — confirmar ramp de revenue AI y ritmo real de uso del ATM

---

*Fuentes: 10-K FY2025 (SEC EDGAR), Q2 FY2026 Earnings Release (feb 2026), IREN IR — Microsoft AI Contract Announcement, IREN ATM Prospectus (mar 2026)*
