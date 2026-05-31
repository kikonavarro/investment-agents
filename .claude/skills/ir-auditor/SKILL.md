---
name: ir-auditor
description: >
  Auditor escéptico de cifras corporativas. Compara las métricas que la empresa
  presenta en sus Investor Relations (EBITDA ajustado, deuda neta ajustada,
  crecimiento orgánico) con las cuentas oficiales (10-K, informes anuales depositados)
  para detectar maquillaje contable, ajustes excesivos o cifras demasiado optimistas.
  Se ejecuta SIEMPRE como parte del pipeline del analyst después de obtener datos del IR.
  También se puede invocar independientemente: "audita las cifras de X", "es creíble lo que dice X",
  "están maquillando los números".
---

# IR Auditor — Auditoría Escéptica de Cifras Corporativas

## Principio fundamental

> Las empresas presentan sus resultados de la forma más favorable posible.
> Tu trabajo es encontrar la diferencia entre lo que dicen y lo que es.
> Asume que el EBITDA ajustado siempre es optimista hasta que demuestres lo contrario.

## Paso 0: Obtener los datos

### Fuentes a contrastar

1. **Presentación de Investor Relations (IR)**: buscar en web
```
WebSearch: "{company_name} investor relations annual results presentation 2024"
WebSearch: "{company_name} investor relations quarterly results"
```
Descargar el PDF y leerlo con Read tool.

2. **Cuentas oficiales depositadas**:
   - **USA**: 10-K ya descargados en `data/valuations/{TICKER}/SEC_filings/`
   - **Europa**: buscar en web
   ```
   WebSearch: "{company_name} annual report 2024 PDF"
   WebSearch: "{company_name} registration document CNMV/CONSOB/FCA"
   ```
   - **UK**: Companies House filing
   - **Italia**: CONSOB / Borsa Italiana

3. **Datos de Yahoo Finance**: ya en el JSON de valoración
   ```
   data/valuations/{TICKER}/{TICKER}_valuation.json
   ```

### Guardar los documentos

```
data/valuations/{TICKER}/IR/
  ├── presentation_annual_2024.pdf
  ├── annual_report_2024.pdf
  └── ir_audit_{fecha}.md
```

## Marco de auditoría — 8 puntos de control

### 1. EBITDA: reported vs adjusted
**Qué buscar:** La empresa suele presentar "EBITDA ajustado" quitando:
- Costes de reestructuración (¿son realmente one-off o recurrentes?)
- Impairments de goodwill
- Costes de adquisición
- Stock-based compensation
- IFRS16 (leases)

**Test:** Calcular la diferencia entre EBITDA reported y EBITDA adjusted.
- Si la diferencia es <5% del EBITDA → OK, ajustes menores
- Si es 5-15% → zona gris, examinar cada ajuste
- Si es >15% → bandera roja. Los "ajustes" son una parte material del resultado

**Preguntas clave:**
- ¿Los costes de reestructuración se repiten cada año? → No son one-off
- ¿Excluyen SBC del EBITDA? → Es un coste real de compensación
- ¿El IFRS16 add-back es enorme? → Compara con alquileres reales pagados en cash flow

### 2. Revenue: reported vs organic vs pro-forma
**Qué buscar:**
- ¿El crecimiento que reportan es orgánico o incluye adquisiciones?
- ¿Usan "like-for-like" o "constant currency" para inflar el crecimiento?
- Si hay adquisición: ¿el revenue pro-forma es consistent con el filing de la empresa adquirida?

**Test:**
- Crecimiento reported vs orgánico: si la diferencia es >5pp, hay componente inorgánico significativo
- Verificar el revenue de la empresa adquirida en sus propios filings pre-adquisición

### 3. Deuda neta: ¿qué excluyen?
**Qué buscar:**
- ¿Excluyen shareholder loans? (son deuda real)
- ¿Excluyen IFRS16 leases? (son compromisos de pago reales)
- ¿Excluyen earn-outs o contingent consideration de M&A?
- ¿Excluyen deuda de filiales (Financial Services, SPVs)?

**Test:** Comparar "deuda neta ajustada" del IR con deuda neta del balance oficial.
- Si la diferencia es >20% → están escondiendo deuda
- Listar cada exclusión y juzgar si es razonable

### 4. FCF: ¿es sostenible o está inflado?
**Qué buscar:**
- FCF = Operating CF - CapEx. ¿Qué incluyen en Operating CF?
- ¿Hay un swing positivo de working capital enorme? → Puede ser timing, no recurrente
- ¿El CapEx reportado incluye M&A? → Debería separarse en "maintenance" vs "growth"
- ¿Hay factoring de receivables? → Infla el operating CF artificialmente

**Test:** FCF / Net Income > 1.5x durante varios años → sospechar de calidad del FCF

### 5. Márgenes: ¿tendencia real o maquillaje?
**Qué buscar:**
- ¿Los márgenes mejoran por eficiencia real o por cambio de mix post-adquisición?
- ¿Comparan con el año anterior o con un año cherry-picked?
- ¿Los targets de margen a medio plazo son realistas vs peers?

**Test:** Comparar la trayectoria de márgenes con peers del sector.
- Si la empresa dice "target 10% EBITDA margin" pero los peers están al 8% → ¿qué los hace especiales?
- Si los márgenes mejoran cada trimestre después de una adquisición → normal (sinergias)
- Si los márgenes mejoran solo ajustando, no reported → bandera roja

### 6. Guidance: ¿historial de cumplimiento?
**Qué buscar:**
- ¿Han cumplido sus guidance anteriores?
- ¿Bajan guidance silenciosamente durante el año?
- ¿El guidance actual depende de supuestos irrealistas?

**Test:** Comparar guidance dado hace 1-2 años con resultados reales.
- Track record de cumplimiento → más creíble
- Historial de profit warnings → menos creíble

### 7. Transacciones con partes vinculadas
**Qué buscar:**
- ¿Hay préstamos de/a accionistas de control?
- ¿Compran/venden activos a empresas del grupo?
- ¿Hay management fees al accionista de control?

**Test:** Buscar en las notas del annual report: "related party transactions"
- Si son materiales (>2% de revenue) → examinar con detalle

### 8. Calidad del auditor y opinión
**Qué buscar:**
- ¿Quién audita? (Big 4 = más fiable, firma local = más riesgo)
- ¿Opinión limpia o con salvedades/qualifications?
- ¿Ha cambiado de auditor recientemente? → Bandera roja

## Estructura del output

```markdown
## Auditoría de Cifras — [TICKER] [Nombre]

### Resumen ejecutivo
**Nivel de confianza: [ALTO / MEDIO / BAJO]**
[2-3 frases sobre si las cifras son creíbles o hay maquillaje]

### Comparación IR vs Cuentas Oficiales

| Métrica | IR Presentation | Cuentas Oficiales | Diferencia | Veredicto |
|---------|----------------|-------------------|------------|-----------|
| Revenue | EUR X.XXM | EUR X.XXM | X% | OK / Alerta |
| EBITDA reported | EUR X.XXM | EUR X.XXM | X% | OK / Alerta |
| EBITDA adjusted | EUR X.XXM | N/A | +X% vs reported | OK / Alerta |
| Deuda neta | EUR X.XXM | EUR X.XXM | X% | OK / Alerta |
| FCF | EUR X.XXM | EUR X.XXM | X% | OK / Alerta |

### Detalle por punto de control

#### 1. EBITDA: reported vs adjusted — [OK / ALERTA / BANDERA ROJA]
[Detalle de cada ajuste, ¿recurrente o genuinamente one-off?]

#### 2. Revenue: organic vs reported — [OK / ALERTA]
[...]

[... resto de los 8 puntos ...]

### Banderas rojas detectadas
- [Lista de alertas, si las hay]

### Conclusión
**¿Son creíbles las cifras del IR?** [Sí / Con reservas / No]
**¿Cambia nuestra valoración?** [No / Sí, ajustar X / Sí, descartar]
**Acción:** [Usar cifras del IR / Usar cifras oficiales / Promediar]

---
*Auditoría generada el [fecha]. Basada en datos públicos disponibles.*
```

## Guardar resultado

Guardar en `data/valuations/{TICKER}/IR/ir_audit_{fecha}.md`

## Reglas

1. **Escepticismo por defecto** — asume que las cifras del IR son optimistas
2. **Datos concretos** — cada alerta debe citar números específicos
3. **No inventar datos** — si no tienes el annual report, dilo
4. **Ser justo** — no todo ajuste es maquillaje. Algunos son legítimos
5. **Conclusión clara** — siempre terminar con "¿son creíbles?" y "¿cambia nuestra valoración?"
