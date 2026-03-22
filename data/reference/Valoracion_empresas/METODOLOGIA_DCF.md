# Metodologia de Valoracion DCF - Guia Completa

## Resumen

Este documento explica paso a paso como el sistema calcula el valor intrinseco de una empresa publica mediante un modelo **Discounted Cash Flow (DCF)** con 3 escenarios.

---

## 1. Datos de Entrada

### Fuentes
| Dato | Fuente |
|------|--------|
| Income Statement, Balance Sheet, Cash Flow | yahooquery (gratuito) |
| Beta, precio actual, market cap | yahooquery |
| Revenue por segmentos | SEC EDGAR XBRL (fallback: segmento unico) |
| Filings 10-K | SEC EDGAR |

### Datos historicos extraidos
- **Revenue** por segmento de negocio (ultimos 4-5 anos)
- **Gross Profit, SG&A, R&D, D&A** (para calcular margenes promedio)
- **CapEx, Working Capital, Impuestos**
- **Deuda total, Cash, Shares Outstanding**
- **Beta** de la accion

---

## 2. Construccion de Assumptions (Supuestos)

### 2.1 Tasa de Crecimiento de Revenue

**Calculo del growth base:**
1. Se calculan tasas de crecimiento historicas: `(Revenue_t / Revenue_t-1) - 1`
2. Se promedian los ultimos 3-5 anos
3. Si hay estimaciones de analistas disponibles, se usan como override
4. Se limita al rango **[-15%, +40%]**

**Proyeccion a 5 anos (tapering):**
- El crecimiento se reduce gradualmente porque es dificil mantener tasas altas a largo plazo

```
Y1 = Growth base (ej: 15.7%)
Y2 = Y1 * 0.9
Y3 = Y1 * 0.8
Y4 = Y1 * 0.7
Y5 = Y1 * 0.6 (o se repite Y4)
```

Para empresas con crecimiento negativo, se asume mejora incremental (+2%, +3%, +4%, +5%).

**Tres escenarios:**

| Escenario | Revenue Growth | Logica |
|-----------|---------------|--------|
| **Base** | Consenso analistas o promedio historico | Caso mas probable |
| **Bull** | Base + prima (30% del base, minimo 3%) | Todo sale bien |
| **Bear** | Base - descuento (misma magnitud) | Escenario adverso |

### 2.2 Margenes Operativos

Se calculan como **promedio historico** de los ultimos anos:

```
Gross Margin   = Gross Profit / Revenue
SG&A %         = SG&A / Revenue
R&D %          = R&D / Revenue
D&A %          = Depreciation / Revenue
CapEx %        = Capital Expenditure / Revenue
Tax Rate       = Tax Provision / Operating Income (max 35%)
```

**Ajustes por escenario:**

| Margen | Base | Bull | Bear |
|--------|------|------|------|
| Gross Margin | Historico | +2pp | -2pp |
| SG&A % | Historico | -1pp | +1pp |
| R&D % | Historico | = | +0.5pp |

**Defaults si no hay datos:**
Gross Margin 40%, SG&A 15%, R&D 5%, D&A 3%, CapEx 4%, Tax Rate 21%

### 2.3 WACC (Weighted Average Cost of Capital)

El WACC es la **tasa de descuento** que refleja el coste de financiacion de la empresa.

**Formula:**
```
WACC = Ke * (E/V) + Kd * (1 - t) * (D/V)
```

Donde:
- `Ke` = Coste del equity (via CAPM)
- `Kd` = Coste de la deuda (5% por defecto)
- `E/V` = Peso del equity = Market Cap / (Market Cap + Deuda Total)
- `D/V` = Peso de la deuda = 1 - E/V
- `t` = Tasa impositiva

**CAPM (Capital Asset Pricing Model):**
```
Ke = Rf + Beta * ERP
```
- `Rf` (Risk-free rate) = 4.5% (rendimiento bono US 10Y)
- `ERP` (Equity Risk Premium) = 5.5%
- `Beta` = De Yahoo Finance (sensibilidad al mercado)

**Ejemplo Apple:** `Ke = 4.5% + 1.0 * 5.5% = 10%`

**Ajustes por escenario:**

| Escenario | WACC |
|-----------|------|
| Base | WACC calculado |
| Bull | WACC - 1pp |
| Bear | WACC + 2pp |

Minimo WACC: 5%

### 2.4 Terminal Value Multiple (Multiplo de Valor Terminal)

Multiplo de EBITDA basado en el **sector** de la empresa:

| Sector | Multiplo Base |
|--------|--------------|
| Technology | 18x |
| Healthcare | 15x |
| Communication | 14x |
| Consumer / Real Estate | 12x |
| Industrial | 11x |
| Financial | 10x |
| Energy | 8x |
| Default | 12x |

**Ajustes por crecimiento:**
- Growth > 20%: +3x
- Growth > 10%: +1x
- Growth < 0%: -2x
- Minimo: 5x

**Ajustes por escenario:**

| Escenario | TV Multiple |
|-----------|------------|
| Base | Sector + ajuste growth |
| Bull | Base + 2x |
| Bear | Base - 3x |

---

## 3. Modelo Financiero (Hoja Model)

### 3.1 Proyeccion de Revenue

```
Revenue_Y1 = Revenue_ultimo_ano * (1 + Growth_Y1)
Revenue_Y2 = Revenue_Y1 * (1 + Growth_Y2)
...
Revenue_Y5 = Revenue_Y4 * (1 + Growth_Y5)
```

El growth rate se selecciona dinamicamente con `OFFSET` segun el escenario elegido (1=Base, 2=Bull, 3=Bear).

### 3.2 De Revenue a EBITDA

```
Revenue
  (-) COGS          = Revenue * (1 - Gross Margin)
  ──────────────────
  = Gross Profit     = Revenue * Gross Margin

  (-) SG&A           = Revenue * SG&A %
  (-) R&D            = Revenue * R&D %
  ──────────────────
  = EBITDA            = Gross Profit - SG&A - R&D
```

### 3.3 De EBITDA a UFCF (Unlevered Free Cash Flow)

```
  EBITDA
  (-) D&A             = Revenue * D&A %
  ──────────────────
  = EBIT               = EBITDA - D&A

  (-) Impuestos        = EBIT * Tax Rate
  ──────────────────
  = NOPAT              = EBIT * (1 - Tax Rate)

  (+) D&A              (se suma de vuelta, no es salida de caja)
  (+/-) Cambio en WC   (cambio en working capital)
  (-) CapEx            = Revenue * CapEx %
  ──────────────────
  = UFCF                = Cash flow disponible para TODOS los inversores
                          (deuda + equity), antes de financiacion
```

**Por que "Unlevered"?** Porque no descuenta intereses de deuda. Representa el cash flow operativo puro de la empresa, independiente de como se financia. El coste de la deuda ya esta incorporado en el WACC.

---

## 4. Valoracion DCF (Hoja Valuation)

### 4.1 Descuento de Cash Flows

Cada UFCF futuro se descuenta al presente usando el WACC:

```
Factor_Descuento_n = 1 / (1 + WACC)^n

PV_UFCF_n = UFCF_n * Factor_Descuento_n
```

**Ejemplo con WACC = 10.4%:**
```
Ano 1: Factor = 1/(1.104)^1 = 0.9058
Ano 2: Factor = 1/(1.104)^2 = 0.8204
Ano 3: Factor = 1/(1.104)^3 = 0.7431
Ano 4: Factor = 1/(1.104)^4 = 0.6731
Ano 5: Factor = 1/(1.104)^5 = 0.6097
```

**Suma PV de UFCFs:**
```
Sum_PV_UFCF = PV_UFCF_1 + PV_UFCF_2 + ... + PV_UFCF_5
```

### 4.2 Terminal Value (Valor Terminal)

El terminal value captura el valor de TODOS los cash flows mas alla del ano 5, asumiendo que la empresa continua operando indefinidamente.

**Metodo: Exit Multiple**
```
Terminal Value = UFCF_Year5 * TV_Multiple
PV_Terminal_Value = Terminal Value / (1 + WACC)^5
```

**Nota:** El TV suele representar el 60-80% del Enterprise Value total. Esto es normal en un DCF - la mayor parte del valor esta en el largo plazo.

### 4.3 Enterprise Value -> Equity Value per Share

```
Enterprise Value (EV)  = Sum_PV_UFCF + PV_Terminal_Value
                         (valor de todos los activos operativos)

(-) Net Debt           = Deuda Total - Cash
                         (lo que se "debe" a los acreedores)

= Equity Value          = EV - Net Debt
                         (valor que le corresponde a los accionistas)

Equity Value per Share = Equity Value / Shares Outstanding
                         (valor intrinseco por accion)

Upside/Downside        = (EVPS / Precio_Actual) - 1
```

---

## 5. Tabla de Sensibilidad

La tabla muestra como varia el valor por accion ante cambios en los dos inputs mas criticos:

- **Filas:** WACC (base +/- 3pp, en incrementos de 1pp) -> 7 valores
- **Columnas:** TV Multiple (base +/- 4x, en incrementos de 2x) -> 5 valores
- **Total:** 35 escenarios de valoracion

**Formula de cada celda:**
```
EVPS = (SUM(UFCF_i / (1+WACC_fila)^i) + UFCF_5 * TV_col / (1+WACC_fila)^5 - Net_Debt) / Shares
```

La celda central (WACC base, TV base) corresponde al escenario seleccionado y se resalta en verde.

---

## 6. Resumen Visual del Flujo Completo

```
DATOS HISTORICOS (yahooquery + SEC)
        |
        v
ASSUMPTIONS
  ├── Revenue Growth (3 escenarios, tapering a 5 anos)
  ├── Margenes (GM, SG&A, R&D, D&A, CapEx, Tax)
  ├── WACC (CAPM: Rf + Beta*ERP, ponderado deuda/equity)
  └── TV Multiple (por sector + ajuste growth)
        |
        v
MODELO FINANCIERO (5 anos proyectados)
  Revenue -> Gross Profit -> EBITDA -> EBIT -> NOPAT -> UFCF
        |
        v
DCF VALUATION
  ├── PV de cada UFCF (descontado a WACC)
  ├── Terminal Value (UFCF_5 * TV Multiple, descontado)
  ├── Enterprise Value = Sum PV + PV Terminal
  ├── Equity Value = EV - Net Debt
  └── Precio por Accion = Equity Value / Shares
        |
        v
TABLA DE SENSIBILIDAD
  WACC x TV Multiple -> 35 valoraciones alternativas
```

---

## 7. Limitaciones del Modelo

1. **Terminal Value dominante:** El TV suele ser 60-80% del EV. Pequenos cambios en el multiplo o WACC tienen gran impacto.
2. **Margenes constantes:** Se asumen margenes estables en la proyeccion. En realidad fluctuan.
3. **Working Capital simplificado:** Se proyecta de forma basica, sin modelar cada componente (AR, AP, inventario).
4. **Un solo segmento de revenue para muchas empresas:** SEC XBRL no siempre reporta segmentos, hay fallback a segmento unico.
5. **WACC estatico:** Se usa un unico WACC para los 5 anos. En realidad puede cambiar si la estructura de capital evoluciona.
6. **Sin ajustes especificos:** No se modelan eventos extraordinarios, M&A, cambios regulatorios, etc.
