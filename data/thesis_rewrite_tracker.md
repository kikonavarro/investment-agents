# Thesis Rewrite Tracker — Abril 2026

## Progreso: 22/26 completadas (4 excluidas)

### S1 — Big Tech Core ✅
- [x] AAPL — $255.92 → FV $226.54 → 🟠 LIGERAMENTE SOBREVALORADA (-13%)
- [x] MSFT — $373.46 → FV $600.16 → 🟢 INFRAVALORADA (+38%)
- [x] GOOG — $294.46 → FV $272.85 → ⚪ VALOR JUSTO (-8%)

### S2 — Big Tech / Growth ✅
- [x] AMZN — $209.77 → FV $202.96 → ⚪ VALOR JUSTO (-3%)
- [x] NFLX — $98.66 → FV $119.19 → 🟡 LIGERAMENTE INFRAVALORADA (+17%)
- [x] TSLA — $360.59 → FV $64.76 (SoP) → 🔴 SOBREVALORADA (-82%)

### S3 — Pagos ✅
- [x] MA — $493.44 → FV $608 → 🟡 LIGERAMENTE INFRAVALORADA (+19%)
- [x] V — $300.80 → FV $401 → 🟢 INFRAVALORADA (+25%)
- [x] PYPL — $45.34 → FV $72.16 → 🟢 INFRAVALORADA (+37%)

### S4 — Consumer Cyclical USA ✅
- [x] NKE — $44.19 → FV $54.23 → 🟡 LIGERAMENTE INFRAVALORADA (+19%)
- [x] MCD — $307.14 → FV $214 → 🟠 LIGERAMENTE SOBREVALORADA (-30%)
- [x] PLAY — $12.35 → FV ~$15 (EV-based) → 🟡 ESPECULATIVA

### S5 — Energía / Commodities ✅
- [x] OXY — $62.97 → FV $58.77 → ⚪ VALOR JUSTO (-7%)
- [x] MAU_PA — €10.73 → FV €9.90 → ⚪ VALOR JUSTO (-8%)
- [x] WCP_TO — C$15.54 → FV C$12.80 → 🟠 LIGERAMENTE SOBREVALORADA (-21%)

### S6 — Internacional ✅
- [x] IVN_TO — C$10.44 → FV C$11.10 (NAV) → ⚪ VALOR JUSTO (-6%)
- [x] MC_PA — €471.05 → FV €558 → 🟡 LIGERAMENTE INFRAVALORADA (+16%)
- [x] NWL_MI — €15.36 → FV €20.00 → 🟡 LIGERAMENTE INFRAVALORADA (+22%)

### S7 — Tech Growth / Healthcare ❌ EXCLUIDA
- [~] NTSK — excluida por usuario
- [~] IREN — excluida por usuario
- [~] OSCR — excluida por usuario

### S8-S9 — Hardware / Industrial / REIT ✅
- [x] CSU_TO — C$2,441 → FV C$2,480 → ⚪ VALOR JUSTO (+2%)
- [x] HPQ — $19.51 → FV $21.80 → 🟡 LIGERAMENTE INFRAVALORADA (+11%)
- [x] DE — $575.71 → FV $518 → 🟠 LIGERAMENTE SOBREVALORADA (-11%)
- [x] VICI — $27.66 → FV $29.40 → ⚪ VALOR JUSTO (+6%)
- [~] SLP — excluida por usuario

## Ranking final por oportunidad (MoS descendente)

| # | Señal | Ticker | Precio | Fair Value | MoS | Nota |
|---|-------|--------|--------|-----------|-----|------|
| 1 | 🟢 | **MSFT** | $373 | $600 | +38% | AI CapEx sell-off, negocio intacto |
| 2 | 🟢 | **PYPL** | $45 | $72 | +37% | Deep value, FCF yield 13% |
| 3 | 🟢 | **V** | $301 | $401 | +25% | Duopolio pagos a descuento |
| 4 | 🟡 | **NWL_MI** | €15 | €20 | +22% | Post-adquisición, sinergias |
| 5 | 🟡 | **MA** | $493 | $608 | +19% | Duopolio pagos |
| 6 | 🟡 | **NKE** | $44 | $54 | +19% | Turnaround, marca icónica |
| 7 | 🟡 | **NFLX** | $99 | $119 | +17% | Ad tier growing |
| 8 | 🟡 | **MC_PA** | €471 | €558 | +16% | Lujo cíclico, China recovery |
| 9 | 🟡 | **HPQ** | $20 | $22 | +11% | Cash cow, 9% shareholder yield |
| 10 | ⚪ | **VICI** | $28 | $29 | +6% | Income play, 6.2% yield |
| 11 | ⚪ | **CSU_TO** | C$2,441 | C$2,480 | +2% | Compounder a fair value |
| 12 | ⚪ | **AMZN** | $210 | $203 | -3% | CapEx distortion |
| 13 | ⚪ | **IVN_TO** | C$10 | C$11 | -6% | Mining ramp-up |
| 14 | ⚪ | **OXY** | $63 | $59 | -7% | Fair a Brent normalizado |
| 15 | ⚪ | **GOOG** | $294 | $273 | -8% | Antitrust risk |
| 16 | ⚪ | **MAU_PA** | €11 | €10 | -8% | Gabón risk |
| 17 | 🟠 | **DE** | $576 | $518 | -11% | Ciclo agro + aranceles |
| 18 | 🟠 | **AAPL** | $256 | $227 | -13% | Premium sin margen |
| 19 | 🟠 | **WCP_TO** | C$16 | C$13 | -21% | WTI overpriced |
| 20 | 🟠 | **MCD** | $307 | $214 | -30% | Deuda + WACC |
| 21 | 🟡 | **PLAY** | $12 | $15 | — | Especulativa, binary |
| 22 | 🔴 | **TSLA** | $361 | $65 | -82% | Narrative stock |

## Bugs corregidos durante la reescritura
1. **SGA bug** (`tools/financial_data.py:718`): Comparaba EBIT implícito vs EBITDA real. Ahora compara EBIT vs EBIT.
2. **Ticker internacional** (`tools/financial_data.py`): Nueva función `_to_yahoo_ticker()` convierte MAU_PA → MAU.PA para yahooquery.

## Notas metodológicas
- Payment networks (MA/V): WACC mín 10%, TV 16-24x
- Energía (OXY/MAU/WCP): Oil price scenarios como driver principal
- Mining (IVN_TO): NAV-based, no DCF
- REITs (VICI): P/FFO y P/AFFO, no DCF estándar
- Content (NFLX): Owner earnings por amortización de contenido
- Distressed (PLAY): EV/EBITDA con leverage analysis
- Narrative stocks (TSLA): Sum-of-Parts con optionalidad
- Cíclicas (DE): DCF mid-cycle normalizado + SoP con banco cautivo
- Serial acquirers (CSU): P/FCF (NI distorsionado por amortización de intangibles)

## Pendiente
- Tesla: análisis dedicado aparte (robotaxi/Optimus deep-dive)
- MCD: análisis dedicado aparte (WACC sensitivity, real estate NAV)
