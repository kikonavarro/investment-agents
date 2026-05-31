---
name: dcf-valuation
description: >
  Valoración de empresas por Descuento de Flujos de Caja (DCF) con mentalidad
  de value investing. Usa esta skill SIEMPRE que necesites valorar una empresa,
  calcular un precio objetivo, estimar el valor intrínseco, o decidir si una
  acción está infravalorada. También aplica cuando el usuario pida un DCF,
  valoración, "cuánto vale esta empresa", análisis financiero con precio objetivo,
  o cualquier variante. Incluye normalización de FCF, múltiples escenarios,
  análisis de sensibilidad y margen de seguridad. Sigue la filosofía de Graham,
  Buffett y Greenwald: ser conservador, pensar como dueño del negocio, y exigir
  margen de seguridad.
---

# DCF Valuation Skill — Value Investing

## Filosofía Fundamental

> "El precio es lo que pagas, el valor es lo que recibes." — Warren Buffett

Esta skill implementa un DCF riguroso con la mentalidad de un inversor value serio.
Los principios que SIEMPRE deben respetarse:

1. **Sé conservador**: Es mejor perder una oportunidad que perder dinero
2. **Normaliza el FCF**: Un solo año no dice nada. Mira la tendencia
3. **El terminal value no es magia**: Si representa >75% de tu valoración, desconfía
4. **Margen de seguridad mínimo 25%**: Si no hay margen, no hay inversión
5. **Entiende el negocio**: Antes de valorar, entiende qué hace la empresa y por qué gana dinero
6. **Garbage in, garbage out**: Un DCF es tan bueno como sus inputs

## Proceso Completo de Valoración

### PASO 1: Descargar y entender los datos

Antes de calcular nada, necesitas los estados financieros de al menos 5 años
(idealmente 10). Datos mínimos requeridos:

```
Income Statement: Revenue, EBIT, Net Income, D&A, Interest Expense, Tax Rate
Balance Sheet: Total Debt, Cash, Total Equity, Shares Outstanding
Cash Flow: Operating Cash Flow, CapEx, Free Cash Flow
Precio actual de la acción
```

Usa `yfinance` para descargar. Ejemplo:

```python
import yfinance as yf

tk = yf.Ticker("AAPL")
income = tk.financials          # Income statement
balance = tk.balance_sheet      # Balance sheet
cashflow = tk.cashflow          # Cash flow statement
info = tk.info                  # Precio actual, market cap, etc.
```

**IMPORTANTE**: yfinance a veces devuelve datos incompletos o con nombres de
columnas inconsistentes. Siempre verifica que los datos tienen sentido antes
de continuar. Lee `references/data_validation.md` para las comprobaciones.

---

### PASO 2: Normalizar el Free Cash Flow

**NUNCA uses el FCF del último año como base del DCF.**

El FCF de un solo año puede estar distorsionado por:
- Gastos extraordinarios o one-offs
- Ciclo económico (empresa cíclica en pico o valle)
- Cambios en working capital temporales
- CapEx de expansión inusualmente alto o bajo

**Método de normalización (por orden de preferencia):**

#### Método A: Mediana de FCF de 5 años (preferido para empresas estables)
```python
def normalize_fcf_median(cashflow_history: dict) -> float:
    """
    Usa la mediana (no media) de los últimos 5 años.
    La mediana es más robusta contra outliers que la media.
    """
    fcf_values = []
    for year_data in cashflow_history.values():
        ocf = year_data.get("Operating Cash Flow", 0)
        capex = abs(year_data.get("Capital Expenditure", 0))
        fcf = ocf - capex
        fcf_values.append(fcf)

    return statistics.median(fcf_values)
```

#### Método B: FCF normalizado por márgenes (para empresas en crecimiento)
```python
def normalize_fcf_margins(financials: dict) -> float:
    """
    Calcula el margen FCF/Revenue mediano y aplícalo al revenue más reciente.
    Útil cuando la empresa crece y el FCF absoluto de hace 5 años no es
    representativo, pero los márgenes son estables.
    """
    margins = []
    for year in financials:
        revenue = year["revenue"]
        fcf = year["fcf"]
        if revenue > 0:
            margins.append(fcf / revenue)

    median_margin = statistics.median(margins)
    latest_revenue = financials[0]["revenue"]
    return latest_revenue * median_margin
```

#### Método C: Owner Earnings de Buffett (para empresas con mucho D&A)
```python
def owner_earnings(financials: dict) -> float:
    """
    Owner Earnings = Net Income + D&A - Maintenance CapEx
    
    El truco está en estimar Maintenance CapEx (lo mínimo para mantener
    el negocio, no para crecer). Regla general:
    - Si la empresa da guidance, úsalo
    - Si no, estima maintenance capex como 50-70% del CapEx total
    - Para empresas asset-light (software, servicios), puede ser 30-40%
    """
    net_income = financials["net_income"]
    da = financials["depreciation_amortization"]
    total_capex = abs(financials["capex"])

    # Estimación conservadora: 70% del capex es mantenimiento
    maintenance_capex = total_capex * 0.70

    return net_income + da - maintenance_capex
```

**Decisión de qué método usar:**
- Empresa estable, FCF predecible → Método A (mediana 5 años)
- Empresa en crecimiento, márgenes estables → Método B (normalización por margen)
- Empresa con alto D&A o capex variable → Método C (owner earnings)
- **En caso de duda → Método A, es el más conservador**

---

### PASO 3: Estimar la tasa de crecimiento

Esta es la parte más difícil y donde más errores se cometen.

**Reglas de oro:**

1. **NUNCA asumas crecimiento >15% sostenido**. Muy pocas empresas en la historia
   han crecido >15% anual durante más de 10 años.

2. **El crecimiento del pasado NO es el crecimiento del futuro**.
   Úsalo como referencia, no como predicción.

3. **Usa la tasa más baja entre**: crecimiento histórico de revenue,
   crecimiento histórico de FCF, y estimaciones de analistas (si las hay).

**Framework para estimar crecimiento:**

```python
def estimate_growth_rate(financials: dict) -> dict:
    """
    Devuelve 3 escenarios de crecimiento.
    
    Lógica:
    1. Calcula CAGR histórico de revenue (5 años)
    2. Calcula CAGR histórico de FCF (5 años)
    3. Toma el MENOR de los dos como "base"
    4. Aplica un haircut según el tipo de empresa
    """
    revenue_cagr = calculate_cagr(revenues, years=5)
    fcf_cagr = calculate_cagr(fcfs, years=5)

    base_growth = min(revenue_cagr, fcf_cagr)

    # Haircuts por tipo de empresa
    # Empresa madura (>50B market cap): máximo 8% growth
    # Empresa mediana (5-50B): máximo 12% growth
    # Empresa pequeña (<5B): máximo 15% growth
    # NUNCA más de 15% sin justificación extraordinaria

    if market_cap > 50e9:
        base_growth = min(base_growth, 0.08)
    elif market_cap > 5e9:
        base_growth = min(base_growth, 0.12)
    else:
        base_growth = min(base_growth, 0.15)

    return {
        "conservative": base_growth * 0.5,   # 50% del base
        "base": base_growth,
        "optimistic": base_growth * 1.3,      # 30% más que base (NO el doble)
    }
```

**Horizonte de proyección:**

- **Por defecto: 5 años** con interpolación lineal de Y1 a Y5 + Exit Multiple sobre EBITDA.
  Consistente con el modelo Python del sistema y con `thesis-writer`.
- **Alternativa: 10 años (2 etapas)** cuando 5 años no capture bien el ciclo de crecimiento
  (ej: empresa en fase de inversión con rentabilidad diferida). Años 1-5 crecimiento estimado,
  años 6-10 decay lineal hacia tasa terminal + Gordon Growth.

```python
def project_growth_rates_5y(growth_y1: float, growth_y5: float) -> list:
    """
    Proyecta 5 años con interpolación lineal (método principal).
    Consistente con el modelo Excel del sistema.
    """
    return [growth_y1 + (growth_y5 - growth_y1) * i / 4 for i in range(5)]
```

---

### PASO 4: Determinar la tasa de descuento (WACC o Hurdle Rate)

Tienes dos opciones:

#### Opción A: WACC calculado (más "académico")
```python
def calculate_wacc(financials: dict, risk_free_rate: float = 0.04) -> float:
    """
    WACC = (E/V × Re) + (D/V × Rd × (1-T))
    
    Donde:
    - E = Market Cap (equity value)
    - D = Total Debt
    - V = E + D
    - Re = Cost of Equity (CAPM)
    - Rd = Cost of Debt
    - T = Tax Rate
    """
    E = financials["market_cap"]
    D = financials["total_debt"]
    V = E + D

    # Cost of equity (CAPM simplificado)
    beta = financials.get("beta", 1.0)
    market_premium = 0.055  # Premium histórico del mercado ~5.5%
    Re = risk_free_rate + beta * market_premium

    # Cost of debt
    interest_expense = financials["interest_expense"]
    Rd = interest_expense / D if D > 0 else 0
    T = financials.get("effective_tax_rate", 0.25)

    wacc = (E/V * Re) + (D/V * Rd * (1 - T))

    # Sanity check: WACC debería estar entre 6% y 15%
    wacc = max(0.06, min(wacc, 0.15))
    return wacc
```

#### Opción B: Hurdle Rate fijo (más "práctico", preferido por value investors)

Muchos value investors, incluido Buffett, simplemente usan una tasa fija
como su "hurdle rate" — el retorno mínimo que exigen.

```
Empresa de alta calidad, predecible    → 8-9%
Empresa normal                          → 10%
Empresa cíclica o con más riesgo        → 11-12%
Empresa small cap o emergente           → 12-15%
```

**Recomendación**: Usa el WACC calculado como referencia, pero si da menos de
10%, usa 10% como mínimo. Mejor equivocarse por conservador.

```python
def get_discount_rate(financials: dict) -> float:
    """Devuelve la tasa de descuento, mínimo 10%."""
    wacc = calculate_wacc(financials)
    return max(wacc, 0.10)
```

---

### PASO 5: Calcular el Terminal Value

El terminal value es el valor de todos los flujos de caja después del período de proyección.
Es la parte más peligrosa del DCF porque suele representar mucho del valor total.

**Método principal: Exit Multiple sobre EBITDA (preferido)**

```
Terminal Value = EBITDA_último_año × Múltiplo_EV/EBITDA
```

El múltiplo se elige por sector/tipo de empresa. Es el mismo método que usa el modelo Python
del sistema (`excel_generator.py`). Más intuitivo y anclado al mercado real.

**Método alternativo: Gordon Growth Model (usar si Exit Multiple da resultados inconsistentes)**

```
Terminal Value = FCF_último_año × (1 + g) / (WACC - g)
```

Usar Gordon Growth cuando:
- El Exit Multiple da un TV >85% del EV (demasiado dependiente del múltiplo elegido)
- No hay múltiplos comparables claros para el sector
- Se quiere validar/contrastar el resultado del Exit Multiple

**Reglas para Gordon Growth (g):**
- NUNCA mayor que inflación + crecimiento real del PIB (2-3% típico)
- Usa 2.5% como default, 2.0% en escenario conservador
- NUNCA >3.5%

**SANITY CHECK OBLIGATORIO:**
```python
def check_terminal_value_weight(terminal_value_pv: float,
                                 total_dcf_value: float) -> str:
    """
    Si el terminal value es >75% del valor total, la valoración
    es frágil. Considerar usar el método alternativo para validar.
    """
    weight = terminal_value_pv / total_dcf_value
    if weight > 0.85:
        return "⚠️ PELIGRO: TV es {:.0%} del valor. Valoración muy especulativa. Validar con método alternativo.".format(weight)
    elif weight > 0.75:
        return "⚠️ PRECAUCIÓN: TV es {:.0%} del valor. Considerar escenario sin TV.".format(weight)
    else:
        return "✅ TV es {:.0%} del valor. Distribución razonable.".format(weight)
```

---

### PASO 6: Juntar todo — El DCF completo

```python
def dcf_valuation(
    revenue: float,
    scenarios: dict,               # bear/base/bull con growth, margins, WACC, TV multiple
    net_debt: float = 0,           # Deuda total - Cash
    shares_outstanding: float = 1,
    years: int = 5,                # 5 por defecto, 10 como alternativa
) -> dict:
    """
    DCF completo. Método principal: 5 años + Exit Multiple sobre EBITDA.
    Consistente con thesis-writer y el modelo Excel del sistema.

    Para cada escenario calcula:
    - EBIT = Revenue × (GM - SGA% - R&D%)  (= Operating Income)
    - EBITDA = EBIT + D&A
    - UFCF = EBIT × (1-tax) + D&A - CapEx  (fórmula estándar)
    - Terminal Value = EBITDA_Y5 × EV/EBITDA_multiple  ← sobre EBITDA (EBIT+D&A), NO EBIT
    - Enterprise Value = PV(UFCFs) + PV(TV)
    - Equity Value = EV - Net Debt
    - Fair Value/acción = Equity / shares
    """
    # [Ver thesis-writer para la implementación detallada]
    pass
```

---

### PASO 7: Tres escenarios SIEMPRE

**NUNCA des un solo precio objetivo.** Siempre calcula tres escenarios:

```python
def run_three_scenarios(financials: dict) -> dict:
    """
    Escenario conservador: lo mínimo razonable
    Escenario base: lo más probable
    Escenario optimista: si todo va bien (pero realista)
    """
    normalized_fcf = normalize_fcf(financials)
    growth = estimate_growth_rate(financials)
    discount_rate = get_discount_rate(financials)
    net_debt = financials["total_debt"] - financials["cash"]
    shares = financials["shares_outstanding"]

    results = {}
    for scenario in ["conservative", "base", "optimistic"]:
        rates = project_growth_rates(
            initial_rate=growth[scenario],
            terminal_rate=0.025 if scenario != "conservative" else 0.02
        )
        dcf = dcf_valuation(
            normalized_fcf=normalized_fcf,
            growth_rates=rates,
            discount_rate=discount_rate + (0.01 if scenario == "conservative" else 0),
            terminal_growth=0.02 if scenario == "conservative" else 0.025,
            net_debt=net_debt,
            shares_outstanding=shares,
        )
        results[scenario] = dcf

    # Precio objetivo ponderado
    # Damos MÁS peso al conservador porque somos value investors
    weighted_price = (
        results["conservative"]["intrinsic_value_per_share"] * 0.40 +
        results["base"]["intrinsic_value_per_share"] * 0.40 +
        results["optimistic"]["intrinsic_value_per_share"] * 0.20
    )

    current_price = financials["current_price"]
    margin_of_safety = (weighted_price - current_price) / weighted_price * 100

    results["weighted_target"] = weighted_price
    results["current_price"] = current_price
    results["margin_of_safety_pct"] = margin_of_safety
    results["signal"] = classify_signal(margin_of_safety)

    return results


def classify_signal(margin_of_safety: float) -> str:
    """
    Señal de inversión basada en margen de seguridad.
    """
    if margin_of_safety >= 40:
        return "🟢 MUY INFRAVALORADA — Oportunidad clara"
    elif margin_of_safety >= 25:
        return "🟢 INFRAVALORADA — Margen de seguridad aceptable"
    elif margin_of_safety >= 10:
        return "🟡 LIGERAMENTE INFRAVALORADA — Margen insuficiente, watchlist"
    elif margin_of_safety >= -10:
        return "⚪ VALOR JUSTO — No hay margen de seguridad"
    elif margin_of_safety >= -25:
        return "🟠 LIGERAMENTE SOBREVALORADA"
    else:
        return "🔴 SOBREVALORADA — Evitar"
```

---

### PASO 8: Análisis de sensibilidad

El DCF es muy sensible a sus inputs. SIEMPRE genera una tabla de sensibilidad.

```python
def sensitivity_analysis(
    base_result: dict,
    financials: dict,
    growth_range: list = [-0.02, -0.01, 0, 0.01, 0.02],
    wacc_range: list = [-0.02, -0.01, 0, 0.01, 0.02],
) -> list[list]:
    """
    Genera una matriz de sensibilidad: filas = growth, columnas = WACC.
    Cada celda = precio objetivo por acción.
    
    Ejemplo de output (tabla):
    
              WACC 8%   WACC 9%   WACC 10%  WACC 11%  WACC 12%
    Growth 2%   $145      $128      $115      $104      $95
    Growth 4%   $168      $148      $132      $119      $108
    Growth 6%   $195      $170      $151      $135      $122
    Growth 8%   $228      $197      $174      $154      $139
    Growth 10%  $269      $229      $200      $176      $158
    
    La celda central es el caso base.
    Las celdas verdes tienen margen de seguridad >25%.
    """
    base_growth = base_result["growth_rate_base"]
    base_wacc = base_result["discount_rate"]
    
    table = []
    for g_delta in growth_range:
        row = []
        for w_delta in wacc_range:
            # Recalcular DCF con estos parámetros
            rates = project_growth_rates(base_growth + g_delta)
            dcf = dcf_valuation(
                normalized_fcf=base_result["normalized_fcf"],
                growth_rates=rates,
                discount_rate=base_wacc + w_delta,
                net_debt=financials["net_debt"],
                shares_outstanding=financials["shares_outstanding"],
            )
            row.append(dcf["intrinsic_value_per_share"])
        table.append(row)
    
    return table
```

---

### PASO 9: Sanity Checks Finales

Antes de presentar resultados, SIEMPRE verifica:

```python
def final_sanity_checks(results: dict, financials: dict) -> list[str]:
    """
    Lista de checks que deben pasar antes de confiar en la valoración.
    """
    warnings = []
    
    # 1. ¿El FCF es positivo?
    if results["normalized_fcf"] <= 0:
        warnings.append("❌ FCF normalizado negativo. DCF no es aplicable. "
                        "Considerar valoración por activos o múltiplos.")
    
    # 2. ¿El terminal value no domina?
    if results["base"]["tv_weight_pct"] > 80:
        warnings.append(f"⚠️ Terminal value es {results['base']['tv_weight_pct']:.0f}% "
                        f"del valor. Valoración poco fiable.")
    
    # 3. ¿El implied P/E tiene sentido?
    net_income = financials["net_income"]
    implied_pe = results["base"]["equity_value"] / net_income if net_income > 0 else 999
    if implied_pe > 30:
        warnings.append(f"⚠️ P/E implícito del DCF = {implied_pe:.1f}x. "
                        f"¿Estás siendo demasiado optimista?")
    elif implied_pe < 5:
        warnings.append(f"⚠️ P/E implícito del DCF = {implied_pe:.1f}x. "
                        f"¿Hay algún riesgo que no estás considerando?")
    
    # 4. ¿El growth rate tiene sentido vs histórico?
    historical_growth = financials.get("revenue_cagr_5y", 0)
    base_growth = results.get("growth_rate_base", 0)
    if base_growth > historical_growth * 1.5:
        warnings.append(f"⚠️ Growth base ({base_growth:.1%}) es mucho mayor que "
                        f"el histórico ({historical_growth:.1%}). Justificar.")
    
    # 5. ¿La empresa tiene demasiada deuda?
    debt_to_equity = financials.get("debt_to_equity", 0)
    if debt_to_equity > 2:
        warnings.append(f"⚠️ Debt/Equity = {debt_to_equity:.1f}. "
                        f"Empresa muy apalancada. DCF más arriesgado.")
    
    # 6. ¿Hay consistencia en el FCF?
    fcf_history = financials.get("fcf_history", [])
    if fcf_history:
        negative_years = sum(1 for f in fcf_history if f < 0)
        if negative_years >= 2:
            warnings.append(f"⚠️ FCF negativo en {negative_years} de los últimos "
                            f"5 años. Empresa con FCF inconsistente.")
    
    return warnings
```

---

### PASO 10: Casos especiales

#### Empresas que NO se deben valorar por DCF:
- **Bancos y financieras**: Usar P/B o Dividend Discount Model
- **REITs**: Usar P/FFO o P/AFFO
- **Startups sin beneficios**: No hay FCF que descontar. Usar revenue multiples
- **Empresas cíclicas en el pico**: El FCF actual no es sostenible. Normalizar con
  cuidado usando un ciclo completo (7-10 años)
- **Empresas en reestructuración**: Usar Sum of Parts (SOTP)

```python
def is_dcf_appropriate(financials: dict) -> tuple[bool, str]:
    """Determina si DCF es el método correcto para esta empresa."""
    sector = financials.get("sector", "").lower()
    
    if any(x in sector for x in ["bank", "financial", "insurance"]):
        return False, "Sector financiero. Usar P/Book o Dividend Discount Model."
    
    if "reit" in sector or "real estate" in sector.lower():
        return False, "REIT. Usar P/FFO o P/AFFO."
    
    fcf_history = financials.get("fcf_history", [])
    if len(fcf_history) >= 3 and all(f < 0 for f in fcf_history[-3:]):
        return False, "FCF negativo 3 años consecutivos. DCF no fiable."
    
    return True, "DCF es aplicable."
```

---

## Output del DCF: Formato de presentación

Cuando presentes los resultados al usuario o a otro agente, usa este formato:

```
════════════════════════════════════════════════════
  DCF VALUATION: APPLE INC (AAPL)
  Fecha: 2025-05-28
════════════════════════════════════════════════════

  Precio actual:         $192.50
  
  ┌─────────────┬──────────┬──────────┬──────────┐
  │             │ Conserv. │   Base   │ Optim.   │
  ├─────────────┼──────────┼──────────┼──────────┤
  │ Growth (1-5)│   3.5%   │   7.0%   │   9.1%   │
  │ WACC        │  11.0%   │  10.0%   │  10.0%   │
  │ Terminal g  │   2.0%   │   2.5%   │   2.5%   │
  │ Target Price│  $155.20 │  $198.40 │  $235.10 │
  │ Margin Safety│  -19.4% │   +3.1%  │  +18.1%  │
  └─────────────┴──────────┴──────────┴──────────┘
  
  Precio objetivo ponderado: $185.30
  Margen de seguridad: -3.7%
  
  Señal: ⚪ VALOR JUSTO — No hay margen de seguridad
  
  Sanity Checks:
  ✅ FCF positivo y consistente
  ✅ Terminal value = 62% del valor total
  ⚠️ P/E implícito = 28.5x — En el límite alto
  
  Análisis de Sensibilidad (precio por acción):
  
              WACC 8%   WACC 9%   WACC 10%  WACC 11%  WACC 12%
  Growth 3%    $168      $152      $138      $127      $117
  Growth 5%    $195      $175      $158      $144      $132
  Growth 7%    $228      $203      $182      $164      $150
  Growth 9%    $269      $236      $210      $188      $171
  Growth 11%   $320      $278      $244      $217      $195

════════════════════════════════════════════════════
```

---

## Referencia rápida de parámetros por defecto

```
Tasa de descuento mínima:    10%
Terminal Value:               Exit Multiple sobre EBITDA (principal)
                              Gordon Growth como alternativa/validación
Período de proyección:        5 años (principal), 10 años (alternativa)
Peso escenario conservador:   40%
Peso escenario base:          40%
Peso escenario optimista:     20%
Margen de seguridad mínimo:   25%
TV weight máximo aceptable:   75% (si >85%, validar con método alternativo)
Growth máximo (large cap):    8% (excepto valoración extrema: diseñar manual)
Growth máximo (mid cap):      12%
Growth máximo (small cap):    15%
Maintenance capex default:    70% del total capex
CapEx en DCF:                 Usar capex_pct histórico real, NO solo D&A
```

## Archivos de referencia adicionales

- `references/data_validation.md` — Cómo validar datos de yfinance
- `references/dcf_implementation.py` — Implementación completa en Python lista para usar
