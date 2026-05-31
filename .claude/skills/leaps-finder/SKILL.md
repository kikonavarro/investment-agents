---
name: leaps-finder
description: >
  Identificar y evaluar oportunidades de LEAPS calls ITM (delta 0.60-0.80, vencimiento >12m)
  en USA. Modo daily: scan automático del universo y devuelve 4-5 ideas. Modo on-demand:
  evalúa un ticker concreto y dice si tiene LEAP atractivo. Detectar: "leaps", "leap call",
  "buena leap", "options long term", mensaje [SCHEDULER] LEAPS, o pregunta sobre call largo
  plazo en un ticker concreto.
---

# LEAPS Finder — Identificación de calls ITM a largo plazo

## Filosofía

LEAPS = Long-term Equity Anticipation Securities. Calls ITM con delta 0.60-0.80 y >12 meses
de vencimiento son una alternativa apalancada al equity directo, con menos theta y comportamiento
similar a la acción. **No son lotería de OTM corto plazo.** Solo se compran sobre tesis con
convicción direccional.

**Reglas duras:**
- Solo USA (liquidez de opciones)
- Calls ITM (strike < spot)
- Delta 0.60-0.80
- Vencimiento >365 días, ideal 500-700 (Jan 2027/2028)
- IV barata (HV percentile bajo) preferible
- NO earnings <14 días
- Open interest >100, spread <5%

**NO incluir:**
- Sugerencia de PMCC (el usuario lo gestiona)
- Sizing de posición
- Stop loss

## Modo 1: Daily scan ([SCHEDULER] LEAPS)

Cuando llega mensaje `[SCHEDULER] LEAPS scan ...` con top candidatos:

1. **Leer el resumen** del mensaje. Ya tienes los datos cuantitativos de los top 10-15.
2. **Para cada uno de los top 4-5**, generar la justificación corta interpretando:
   - **Pullback**: si `from_high_pct` < -20%, es entrada a precio descontado
   - **Sector/momentum**: usa tu conocimiento del sector
   - **Catalizadores conocidos**: turnaround, earnings recovery, ciclo, M&A
   - **Riesgo principal** en 1 línea
3. **WebSearch opcional** si necesitas confirmar un catalizador concreto (earnings recientes,
   noticias). No abusar — el scan diario debe ser rápido.
4. **Componer mensaje Telegram** con formato de abajo. **4-5 ideas máximo.**
5. **Responder con `python tools/check_inbox.py respond <msg_id> --text "..."`**

### Formato del mensaje (cada idea)

```
{TICKER} — LEAP Call {EXPIRY} ${STRIKE} (Δ{DELTA})
Prima: ${MID} | Break-even: ${BE} | Acción: ${SPOT}
HV percentile: {PCT}% ({barata|media|cara}) | OI: {OI}

Por qué: {3-4 líneas — catalizador, valoración rápida, momentum}
Riesgo principal: {1 línea}
```

### Convenciones de "barata/media/cara"

- HV percentile 0-30 → "barata"
- 30-70 → "media"
- 70-100 → "cara" (opciones caras, considerar si vale la pena)

### Cabecera del mensaje

```
🎯 LEAPS scan {fecha} — 5 ideas

[idea 1]

[idea 2]
...
```

## Modo 2: On-demand (pregunta sobre un ticker)

Cuando el usuario pregunta "¿buena LEAP en NKE?", "qué tal una leap en Tesla", etc:

1. **Ejecutar:** `python -m tools.leaps_scanner TICKER`
2. **Interpretar el JSON devuelto:**
   - Si `ok: false` → explicar el motivo (`no_leap_match`, `earnings_in_Xd`, `no_price`)
   - Si `ok: true` → presentar el LEAP con justificación completa
3. **Hacer un análisis fundamental rápido** (no tesis completa):
   - Si existe tesis previa en `data/valuations/{TICKER}/`, usarla
   - Si no, WebSearch breve sobre catalizadores actuales y consenso
4. **Responder con análisis más profundo que en modo daily**: 6-8 líneas de "por qué",
   incluir contexto de valoración (PER, FCF yield si lo tienes), comparar con equity directo
   (leverage implícito = spot/prima).
5. **Veredicto explícito al final**: "Atractiva", "Pasable", "Evitar", con razón.

### Cálculo de leverage

Leverage implícito = `spot / prima`. Si NKE $44.69 con LEAP $12.03, leverage = 3.7x. Esto significa
que cada 1% de movimiento en NKE mueve la LEAP ~Δ × leverage ≈ 0.73 × 3.7 = 2.7%.

Mencionar esto explícitamente en el modo on-demand.

## Limitaciones técnicas a comunicar al usuario

- **"IV percentile" es un proxy** basado en HV (volatilidad realizada) del subyacente, no
  IV histórica del contrato (yfinance no la expone). Si HV alta significa que el subyacente
  ha sido volátil recientemente, normalmente correlaciona con IV alta.
- **Delta calculado vía Black-Scholes** desde IV de yfinance. Suficientemente preciso para
  filtrado, no para market-making.
- **Earnings dates** son best-effort de yfinance. Verificar si una idea va a salir y la
  fecha está cerca (<3 semanas) — usar WebSearch.

## Output: dónde guardar

- Daily scans: el JSON ya queda en `data/leaps/scan_YYYYMMDD_HHMMSS.json` (lo genera el
  scheduler). No necesitas guardar nada más.
- On-demand: no se persiste, solo se responde.

## Errores a evitar

- **No recomendar nunca una LEAP sin justificación fundamental.** Apalancarse sin convicción
  es la receta para perder.
- **No mezclar tickers fuera del universo de USA líquido.** Si el usuario pregunta por un
  ticker europeo (.MC, .PA, .L), responder que las LEAPS no son viables ahí por liquidez.
- **No inventar precios o griegas.** Si el scanner no encuentra match, decirlo.
- **No omitir el riesgo principal.** Aunque corto, debe estar.
