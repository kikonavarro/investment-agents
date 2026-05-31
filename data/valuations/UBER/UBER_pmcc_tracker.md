# UBER — Poor Man's Covered Call (PMCC) — Seguimiento

**Inicio:** 2026-05-11
**Tesis subyacente:** `UBER_tesis_inversion.md` (FV base $94, bear $65, bull $140)

---

## 1. Pierna larga (LEAP)

| Campo                  | Valor                          |
| ---------------------- | ------------------------------ |
| Tipo                   | Long Call                      |
| Vencimiento            | 2027-12-17 (Dec'27, ~585 días) |
| Strike                 | $60                            |
| Prima pagada           | $27.90                         |
| Delta inicial          | 0.79                           |
| Coste total            | $2.790                         |
| Spot UBER en entrada   | $76.24                         |
| Break-even al venc.    | $87.90 (+15.3% vs spot)        |
| Valor intrínseco       | $16.24                         |
| Valor temporal         | $11.66 (42% prima)             |

**Capital eficiencia:** controla equivalente a 79 acciones ($6.022) por $2.790 → 2.16x apalancamiento sobre acciones.

---

## 2. Reglas de venta de calls cortas (PMCC weekly/monthly)

### Selección del strike

- **DTE objetivo:** 30-40 días
- **Delta objetivo:** 0.15-0.25 (OTM)
- **Prima objetivo:** ~$1.00 ($100)
- **Strike mínimo:** nunca por debajo de $85 (10%+ OTM siempre — protege upside)
- **Regla de oro:** si no estarías cómodo "vendiendo" tu LEAP al precio del strike, NO lo vendas

### Cuándo NO vender

- Calls que crucen **earnings** (próximos: 6 ago'26, 5 nov'26, 5 feb'27, 5 may'27, 5 ago'27, 5 nov'27)
- Calls que crucen **mediados de junio 2026** (Tesla Robotaxi launch — evento binario)
- Si UBER < $68 → pausa 1-2 ciclos
- Si delta de tu LEAP < 0.65 → el corto come demasiado

### Cierre / Roll del corto

| Situación                          | Acción                                                 |
| ---------------------------------- | ------------------------------------------------------ |
| Profit del corto ≥ 50%             | **Cerrar** y reabrir nuevo ciclo                      |
| 7 DTE quedan y aún OTM             | Cerrar si profit ≥ 30%, o dejar expirar               |
| Delta corto > 0.30                 | **Roll** arriba y fuera (mismo crédito o débito mín.) |
| Acción rompe strike corto          | Roll a 45 DTE strike +2.5/+5, evitar débito           |
| Imposible rolar sin débito grande  | Cerrar corto, asumir pérdida, evaluar tesis           |

---

## 3. Registro de operaciones cortas

| #  | Fecha apertura | Vencimiento | Strike | Prima cobrada | Acción al cierre | Fecha cierre | Resultado | Notas                |
| -- | -------------- | ----------- | ------ | ------------- | ---------------- | ------------ | --------- | -------------------- |
| 1  |                |             |        |               |                  |              |           |                      |
| 2  |                |             |        |               |                  |              |           |                      |
| 3  |                |             |        |               |                  |              |           |                      |
| 4  |                |             |        |               |                  |              |           |                      |
| 5  |                |             |        |               |                  |              |           |                      |
| 6  |                |             |        |               |                  |              |           |                      |
| 7  |                |             |        |               |                  |              |           |                      |
| 8  |                |             |        |               |                  |              |           |                      |
| 9  |                |             |        |               |                  |              |           |                      |
| 10 |                |             |        |               |                  |              |           |                      |
| 11 |                |             |        |               |                  |              |           |                      |
| 12 |                |             |        |               |                  |              |           |                      |

**Acumulado a fecha:** Income bruto $___ | Roles débito $___ | Income neto $___

---

## 4. Triggers de salida total

| Trigger                                          | Acción                                                                   |
| ------------------------------------------------ | ------------------------------------------------------------------------ |
| UBER < $60                                       | Cerrar todo. Revisar tesis. LEAP ≈ $5-8                                  |
| UBER > $130 sin mejora fundamental               | Cerrar LEAP (tomar +90% beneficio), no esperar a vencimiento              |
| Gross bookings < +12% dos trimestres seguidos    | Cerrar todo. La tesis se rompe                                            |
| Reclasificación drivers en CA o Platform Dir. UE | Re-evaluar bear case. Probable cierre parcial                             |
| Tesla Robotaxi capta >10% market share USA       | Cierre defensivo escalonado                                               |
| Quedan < 90 días en LEAP                         | Cerrar o rolar a Jun'28/Dec'28 si la tesis sigue intacta                  |

---

## 5. Escenarios payoff Dec'27 (referencia rápida)

| UBER Dec'27 | LEAP valor | P/L LEAP    | + Income est. | P/L total       | % sobre $2.790 |
| ----------- | ---------- | ----------- | ------------- | --------------- | -------------- |
| $50         | $0         | -$2.790     | $800          | -$1.990         | **-71%**       |
| $60         | $0         | -$2.790     | $1.000        | -$1.790         | -64%           |
| $70         | $10        | -$1.790     | $1.200        | -$590           | -21%           |
| $80         | $20        | -$790       | $1.400        | +$610           | +22%           |
| $87.90 BE   | $27.90     | $0          | $1.500        | +$1.500         | +54%           |
| $95 base    | $35        | +$710       | $1.600        | +$2.310         | **+83%**       |
| $110        | $50        | +$2.210     | $1.700        | +$3.910         | +140%          |
| $130        | $70        | +$4.210     | $1.700*       | +$5.910         | +212%          |
| $140 bull   | $80        | +$5.210     | $1.700*       | +$6.910         | +248%          |

*Income capped por roles defensivos si rompe strike corto repetidamente.

---

## 6. Notas fiscales (España)

- Cada cierre de corto = ganancia/pérdida patrimonial (declarar en IRPF base del ahorro)
- Roles cuentan como cierre + apertura nueva
- LEAP solo computa al cierre/vencimiento
- Llevar registro limpio de fechas y primas — Hacienda lo pide

---

## 7. Revisión periódica

- **Semanal:** estado del corto (delta, profit %), DTE, próximos earnings
- **Mensual:** P/L acumulado, comparar con tesis subyacente
- **Trimestral:** earnings UBER, releer tesis, validar que sigue vigente
- **Annual:** decisión sobre roll de la LEAP a vencimiento más lejano

---

**Documento vivo. Actualizar tras cada operación.**
