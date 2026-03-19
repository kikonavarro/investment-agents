# Data Validation: Cómo verificar datos de yfinance

## Problemas comunes con yfinance

yfinance es gratuito y útil, pero tiene limitaciones. Siempre verifica antes de calcular.

### 1. Datos faltantes o None

```python
def validate_financial_data(ticker_data: dict) -> list[str]:
    """
    Verifica que los datos mínimos para un DCF están presentes.
    Devuelve lista de problemas encontrados.
    """
    problems = []
    
    required_fields = {
        "income": ["Total Revenue", "EBIT", "Net Income"],
        "balance": ["Total Debt", "Cash And Cash Equivalents", 
                     "Stockholders Equity", "Ordinary Shares Number"],
        "cashflow": ["Operating Cash Flow", "Capital Expenditure"],
    }
    
    for statement, fields in required_fields.items():
        data = ticker_data.get(statement)
        if data is None or data.empty:
            problems.append(f"❌ {statement} completo está vacío")
            continue
        for field in fields:
            if field not in data.index:
                # yfinance a veces usa nombres alternativos
                alternatives = get_alternative_names(field)
                found = any(alt in data.index for alt in alternatives)
                if not found:
                    problems.append(f"⚠️ Campo '{field}' no encontrado en {statement}")
    
    return problems


def get_alternative_names(field: str) -> list[str]:
    """yfinance no es consistente con los nombres de campos."""
    alternatives = {
        "Total Revenue": ["Revenue", "Total Revenue"],
        "Cash And Cash Equivalents": ["Cash", "Cash And Short Term Investments",
                                       "Cash Financial", "Cash Cash Equivalents And Short Term Investments"],
        "Total Debt": ["Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"],
        "Capital Expenditure": ["Capital Expenditure", "CapEx"],
        "Stockholders Equity": ["Stockholders Equity", "Total Equity Gross Minority Interest",
                                 "Common Stock Equity"],
        "Ordinary Shares Number": ["Ordinary Shares Number", "Share Issued"],
    }
    return alternatives.get(field, [field])
```

### 2. Verificación de consistencia temporal

```python
def check_temporal_consistency(financials: dict) -> list[str]:
    """
    Verifica que los datos cubren suficientes años y son consistentes.
    """
    problems = []
    
    # ¿Tenemos al menos 5 años?
    years_available = len(financials.get("revenue_history", []))
    if years_available < 5:
        problems.append(f"⚠️ Solo {years_available} años de datos. Mínimo recomendado: 5")
    
    # ¿Los años son consecutivos?
    dates = financials.get("dates", [])
    for i in range(1, len(dates)):
        diff = (dates[i-1] - dates[i]).days
        if diff > 400:  # Más de ~13 meses entre reportes
            problems.append(f"⚠️ Gap de {diff} días entre reportes en {dates[i]}")
    
    return problems
```

### 3. Verificación de coherencia entre estados financieros

```python
def check_cross_statement_coherence(financials: dict) -> list[str]:
    """
    Los números entre estados financieros deben cuadrar.
    Si no cuadran, los datos pueden estar corruptos.
    """
    problems = []
    
    # Net Income debe ser similar en Income Statement y Cash Flow
    ni_income = financials.get("net_income_is")  # Del Income Statement
    ni_cashflow = financials.get("net_income_cf")  # Del Cash Flow Statement
    
    if ni_income and ni_cashflow:
        diff_pct = abs(ni_income - ni_cashflow) / abs(ni_income) * 100
        if diff_pct > 5:
            problems.append(f"⚠️ Net Income difiere {diff_pct:.1f}% entre IS y CF. "
                           f"IS: {ni_income:,.0f}, CF: {ni_cashflow:,.0f}")
    
    # CapEx no debería ser mayor que Revenue (sería muy inusual)
    capex = abs(financials.get("capex", 0))
    revenue = financials.get("revenue", 1)
    if capex > revenue:
        problems.append(f"⚠️ CapEx ({capex:,.0f}) > Revenue ({revenue:,.0f}). Verificar datos.")
    
    # Debt to equity no debería ser negativo
    equity = financials.get("equity", 0)
    if equity < 0:
        problems.append(f"⚠️ Equity negativo ({equity:,.0f}). Empresa con más deuda que activos.")
    
    return problems
```

### 4. Manejo seguro de datos de yfinance

```python
def safe_get(data, field: str, default=0):
    """
    Extrae un campo de un DataFrame de yfinance de forma segura.
    Maneja None, NaN, y campos faltantes.
    """
    try:
        if data is None or data.empty:
            return default
        if field in data.index:
            value = data.loc[field].iloc[0]  # Año más reciente
            if pd.isna(value):
                return default
            return float(value)
        # Intentar nombres alternativos
        for alt in get_alternative_names(field):
            if alt in data.index:
                value = data.loc[alt].iloc[0]
                if pd.isna(value):
                    return default
                return float(value)
        return default
    except (IndexError, KeyError, TypeError):
        return default


def extract_history(data, field: str, years: int = 5) -> list[float]:
    """
    Extrae historial de un campo (ej: Revenue de los últimos 5 años).
    Devuelve lista ordenada del más antiguo al más reciente.
    """
    try:
        if data is None or data.empty:
            return []
        for name in [field] + get_alternative_names(field):
            if name in data.index:
                row = data.loc[name]
                values = [float(v) for v in row.values[:years] if pd.notna(v)]
                return list(reversed(values))  # Más antiguo primero
        return []
    except (KeyError, TypeError):
        return []
```

### 5. Monedas y unidades

```python
def check_currency(info: dict) -> str:
    """
    Verifica la moneda de los estados financieros.
    IMPORTANTE: yfinance reporta en la moneda de los estados financieros,
    que puede ser diferente a la moneda de cotización.
    
    Ejemplo: BATS.L cotiza en GBp (peniques) pero reporta en GBP (libras).
    Ejemplo: SAP.DE cotiza en EUR y reporta en EUR (ok).
    Ejemplo: NESN.SW cotiza en CHF y reporta en CHF (ok).
    """
    financial_currency = info.get("financialCurrency", "USD")
    quote_currency = info.get("currency", "USD")
    
    if financial_currency != quote_currency:
        return (f"⚠️ Moneda de estados financieros ({financial_currency}) "
                f"≠ moneda de cotización ({quote_currency}). "
                f"Asegúrate de que el precio y el DCF están en la misma moneda.")
    
    return f"✅ Moneda consistente: {financial_currency}"
```
