---
name: screener-ranking
description: >
  Ranking cualitativo de candidatas de inversión value. Usa esta skill cuando
  recibas resultados del screener cuantitativo (top 15 candidatas con métricas)
  y necesites evaluarlas cualitativamente para seleccionar las mejores 5.
  También aplica para mensajes del scheduler con tag [SCHEDULER] Screener.
---

# Screener Ranking — Evaluación cualitativa de candidatas value

## Input

Recibes una lista de ~15 empresas que pasaron filtros cuantitativos (P/E, P/B, dividend yield,
market cap, etc.). Tu trabajo es evaluarlas cualitativamente y rankear las 5 mejores.

## Criterios de evaluación (por orden de importancia)

### 1. Calidad del negocio (peso 30%)
- ¿Tiene moat? (switching costs, network effects, marca, escala)
- ¿Revenue recurrente o transaccional?
- ¿Márgenes estables o volátiles?
- ¿ROIC > WACC sostenido?

### 2. Razón de la infravaloración (peso 25%)
- **Buena razón** (comprar): problema temporal, sector out of favor, mercado overreaccionando
- **Mala razón** (evitar): declive estructural, disrupción tecnológica, pérdida de moat, fraude

### 3. Solidez financiera (peso 20%)
- Deuda manejable (Debt/Equity < 1.5, interest coverage > 5x)
- FCF positivo y consistente
- Sin necesidad de ampliaciones de capital

### 4. Management y capital allocation (peso 15%)
- ¿Directiva alineada? (skin in the game, historial de M&A)
- ¿Buybacks inteligentes o destructores de valor?
- ¿Dividendo sostenible?

### 5. Catalizadores a 12-24 meses (peso 10%)
- ¿Hay algo que pueda desbloquear valor? (spin-off, nuevo producto, cambio regulatorio)
- ¿O es una "trampa de valor" sin catalizador?

## Señales de alerta (descartar automáticamente)
- FCF negativo 3+ años consecutivos
- Sector en declive estructural sin plan de transición
- Historial de dilución masiva (shares outstanding creciendo >5%/año)
- Fraude contable o restating reciente
- P/E bajo por earnings no sostenibles (pico cíclico)

## Output

Para cada candidata evaluada, dar:
- **Ticker + nombre**
- **Puntuación 1-10** (media ponderada de los 5 criterios)
- **Razón concisa** (1-2 frases: por qué sí o por qué no)
- **Señal**: COMPRAR / WATCHLIST / EVITAR

Formato para el top 5:
```
1. TICKER — Nombre (puntuación X/10)
   Razón: [por qué es buena inversión]
   Señal: COMPRAR a $XX-$XX

2. ...
```

Formato para descartadas:
```
- TICKER: [razón concreta del descarte en 1 frase]
```
