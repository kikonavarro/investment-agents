# Guía de Uso — Sistema Multi-Agente de Inversión

Un asistente de inversión value que descarga datos reales, calcula valoraciones y
redacta análisis, tesis y tweets usando la API de Claude. Todo desde la terminal.

---

## Instalación rápida

```bash
# 1. Clona o descarga el proyecto
cd investment-agents

# 2. Instala las dependencias
pip install -r requirements.txt

# 3. Crea el archivo .env con tu clave de Anthropic
echo "ANTHROPIC_API_KEY=sk-ant-tu-clave-aqui" > .env

# 4. Ya puedes usarlo
python main.py --help
```

Consigue tu API key en: https://console.anthropic.com

---

## Qué puede hacer

| Qué quieres | Comando |
| ----------- | ------- |
| Analizar una empresa | `python main.py --analyst AAPL` |
| Analizar varias a la vez | `python main.py --analyst AAPL MSFT BATS.L` |
| Análisis completo + tesis Word | `python main.py --thesis AAPL --save` |
| Ver el estado de tu cartera | `python main.py --portfolio status` |
| Actualizar precios de cartera | `python main.py --portfolio update_prices` |
| Buscar ideas value (screener) | `python main.py --screener` |
| Generar tweets de un análisis | `python main.py --tweets TEF.MC` |
| Escribir artículo para Substack | `python main.py --article "Por qué el tabaco sigue siendo value"` |
| Hablar en lenguaje natural | `python main.py "Analiza Telefónica y escribe la tesis"` |
| Modo interactivo | `python main.py` |

---

## Los agentes explicados

### Analyst — Analista financiero

Descarga los estados financieros reales de la empresa (hasta 10 años),
calcula el valor intrínseco por DCF en tres escenarios y pide a Claude
que interprete los resultados.

**Lo que hace por ti:**
- Descarga income statement, balance sheet y cash flow de yfinance
- Calcula FCF, márgenes, ROIC, ROE, deuda
- Hace el DCF con escenarios conservador / base / optimista
- Busca las últimas noticias de la empresa
- Claude interpreta todo y da una señal: INFRAVALORADA / VALOR JUSTO / SOBREVALORADA

**Ejemplos:**
```bash
python main.py --analyst AAPL
python main.py --analyst TEF.MC
python main.py --analyst BATS.L
python main.py --analyst SAN.MC BBVA.MC BKT.MC      # Varias a la vez
```

**Output de ejemplo:**
```
↑ BATS.L | INFRAVALORADA
  Precio actual : 27.80
  Precio objetivo: 38.50
  Margen seguridad: +38.5%
  Resumen: British American Tobacco cotiza con descuento significativo...
  Fortalezas: FCF extraordinariamente estable | Dividendo del 9%
  Riesgos: Declive estructural del tabaco | Regulación creciente
```

> **Coste aproximado:** ~$0.01 por análisis

---

### Thesis Writer — Redactor de tesis

Recibe el análisis del Analyst y redacta una tesis de inversión completa
en formato Markdown (y Word si usas `--save`).

La tesis incluye: resumen ejecutivo, descripción del negocio, análisis
financiero, valoración DCF, riesgos, catalizadores y conclusión.

**Ejemplos:**
```bash
# Análisis + tesis en pantalla y guardada como .md y .docx
python main.py --thesis BATS.L --save

# Sin guardar (solo en pantalla)
python main.py --thesis AAPL
```

Los archivos se guardan en:
- `data/analyses/YYYYMMDD_AAPL_tesis.md`
- `data/reports/YYYYMMDD_AAPL_tesis.docx`

> **Coste aproximado:** ~$0.06 por tesis completa

---

### Social Media — Generador de tweets

Genera un hilo de Twitter/X (5-8 tweets) a partir de un análisis.
Tono profesional, datos concretos, máx. 280 caracteres por tweet.
Siempre incluye el disclaimer "No es consejo de inversión".

**Ejemplos:**
```bash
python main.py --tweets AAPL
python main.py --tweets TEF.MC
```

**Output de ejemplo:**
```
[1] 🔍 Análisis de $BATS.L (British American Tobacco)
    Precio actual: 27.80 GBP | Objetivo: 38.50 GBP | Upside: +38%

[2] 📊 Los números no mienten:
    • FCF: $9.8B al año (estabilísimo)
    • Dividendo: 9% de yield
    • Deuda controlada tras reducción agresiva

[3] ⚠️ Los riesgos son reales:
    Volúmenes de tabaco cayendo ~3% anual. El negocio shrinka.
    Pero el precio ya lo descuenta (y con creces).
    ...
```

> **Coste aproximado:** ~$0.002 por hilo

---

### Portfolio Tracker — Gestor de cartera

Lee y actualiza tu cartera desde un archivo Excel (`data/mi_cartera.xlsx`).
Soporta acciones (precio automático vía yfinance) y fondos indexados
(precio manual que tú introduces).

**Acciones disponibles:**

```bash
# Ver estado de la cartera con P&L
python main.py --portfolio status

# Actualizar precios automáticos (acciones con ticker)
python main.py --portfolio update_prices
```

**Para añadir posiciones o fondos, edita directamente el Excel** en
`data/mi_cartera.xlsx`. Tiene tres pestañas:

- **Posiciones** — todas tus posiciones (acciones y fondos)
- **Transacciones** — historial de compras y ventas
- **Watchlist** — empresas que sigues con precio de entrada objetivo

**Columnas clave de Posiciones:**

| Columna | Para acciones | Para fondos |
| ------- | ------------- | ----------- |
| Ticker | BATS.L, SAN.MC... | (vacío) |
| Source | `auto` | `manual` |
| Shares / Inv.Amount | Número de acciones | Dinero invertido (€) |
| Avg Price / Cur.Value | Precio medio de compra | Valor actual del fondo |
| Target | Precio objetivo | — |
| Stop Loss | Precio de corte | — |

> **Coste aproximado:** ~$0.001 por consulta

---

### Screener — Buscador de ideas value

Escanea un universo de acciones (S&P 500, IBEX 35, EuroStoxx 600),
aplica filtros cuantitativos y pide a Claude que evalúe y rankee
las mejores candidatas.

**Filtros disponibles:**

| Filtro | Criterios |
| ------ | --------- |
| `graham_default` | P/E ≤15, P/B ≤1.5, Current Ratio ≥1.5, D/E ≤0.5 |
| `value_aggressive` | P/E ≤20, FCF Yield ≥5%, ROIC ≥10% |
| `bargain_hunter` | P/E ≤10, P/B ≤0.8, D/E ≤0.3 |

```bash
# Screener con filtros Graham (por defecto)
python main.py --screener

# Con filtro específico, guardando el informe
python main.py --screener value_aggressive --save
```

> ⚠️ El screener tarda 2-5 minutos porque descarga datos de todos los tickers.
> Es normal. Claude solo interviene al final con las top 15 candidatas.

> **Coste aproximado:** ~$0.005 por screener completo

---

### Content Writer — Articulista de Substack

Escribe artículos de 1500-2500 palabras en español sobre inversión value.
Puedes darle cualquier tema, con o sin datos de soporte.

```bash
python main.py --article "Por qué el tabaco sigue siendo una inversión value" --save
python main.py --article "Cómo analizar bancos europeos con value investing"
python main.py --article "El caso para invertir en empresas aburridas y rentables"
```

Los artículos se guardan en `data/analyses/` si usas `--save`.

> **Coste aproximado:** ~$0.06 por artículo (~2000 palabras)

---

## Lenguaje natural (modo orquestado)

Puedes escribir lo que quieres en lenguaje natural y el sistema decide
qué agentes activar y en qué orden.

```bash
python main.py "Analiza Apple"
python main.py "Analiza TEF.MC y escribe la tesis"
python main.py "Busca ideas value en el S&P 500 y analiza las 3 mejores"
python main.py "¿Cómo va mi cartera?"
python main.py "Analiza BATS.L y genera el hilo de tweets"
```

---

## Modo interactivo

Si ejecutas `python main.py` sin argumentos, entra en modo conversación:

```
Sistema de inversión — escribe 'q' para salir, 'help' para ayuda

>> Analiza Santander
>> ¿Cómo va mi cartera?
>> Escribe un artículo sobre los REITs europeos
>> q
```

---

## Automatización (scheduler)

Puedes dejar el scheduler corriendo en segundo plano para que:
- **Cada día a las 09:00** actualice precios y detecte alertas
- **Cada lunes a las 08:00** corra el screener Graham automáticamente

```bash
# Iniciar el scheduler (déjalo en una terminal en segundo plano)
python scheduler.py

# O ejecutar tareas manualmente cuando quieras
python scheduler.py --now daily     # Actualiza precios + alertas ahora
python scheduler.py --now weekly    # Corre el screener ahora
```

**Las alertas** te avisan cuando:
- Una acción llega a tu precio objetivo (`TARGET ALCANZADO`)
- Una acción baja a tu stop loss (`STOP LOSS`)
- Un fondo manual lleva más de 30 días sin actualizar

Los logs se guardan en `data/logs/`.

---

## Tickers — formatos por mercado

| Mercado | Formato | Ejemplos |
| ------- | ------- | -------- |
| EE.UU. (NYSE/NASDAQ) | Sin sufijo | `AAPL`, `MSFT`, `BRK-B` |
| España (BME) | `.MC` | `SAN.MC`, `TEF.MC`, `ITX.MC` |
| Reino Unido (LSE) | `.L` | `BATS.L`, `GSK.L`, `SHEL.L` |
| Alemania (XETRA) | `.DE` | `VOW3.DE`, `SAP.DE`, `BMW.DE` |
| Francia (Euronext) | `.PA` | `MC.PA`, `OR.PA`, `BNP.PA` |
| Suiza (SIX) | `.SW` | `NESN.SW`, `NOVN.SW` |

---

## Costes estimados (referencia)

| Operación | Coste aprox. |
| --------- | ------------ |
| Análisis de una empresa | ~$0.01 |
| Análisis + tesis completa | ~$0.07 |
| Hilo de tweets | ~$0.002 |
| Estado de cartera | ~$0.001 |
| Screener completo | ~$0.005 |
| Artículo Substack | ~$0.06 |
| Pipeline completo (análisis + tesis + tweets) | ~$0.08 |

Con un uso moderado de 5-10 análisis por semana: **~$5-15 al mes**.

---

## Archivos generados

```
data/
├── analyses/          ← Análisis JSON y tesis Markdown
│   ├── 20260302_AAPL_analysis.json
│   └── 20260302_AAPL_tesis.md
├── reports/           ← Documentos Word y reports del screener
│   ├── 20260302_AAPL_tesis.docx
│   └── 20260302_screener_report.md
├── logs/              ← Logs del scheduler y alertas
│   ├── scheduler.log
│   └── alerts_2026-03-02.txt
└── mi_cartera.xlsx    ← Tu cartera (editar manualmente)
```

---

## Preguntas frecuentes

**¿De dónde vienen los datos financieros?**
De Yahoo Finance a través de la librería yfinance. Son datos reales y gratuitos,
con un pequeño delay respecto al mercado.

**¿El análisis DCF es fiable?**
El DCF usa FCF histórico y lo proyecta. Es un punto de partida para pensar,
no una predicción. Úsalo junto con tu propio criterio.

**¿Por qué el scheduler no me avisa por email/Telegram?**
De momento solo genera logs en `data/logs/`. Puedes añadir notificaciones
integrando un bot de Telegram o SMTP si lo necesitas.

**¿Puedo analizar fondos de inversión o ETFs?**
El analyst está optimizado para acciones con estados financieros. Para ETFs
los datos financieros no tienen sentido. Úsalos solo en la cartera como fondos
manuales.

**¿Funciona con empresas españolas?**
Sí. Usa el sufijo `.MC` para la bolsa española: `TEF.MC`, `SAN.MC`, `ITX.MC`, etc.

---

*Este sistema es una herramienta de análisis personal. No constituye consejo de inversión.*
*Invierte siempre con tu propio criterio y conocimiento de los riesgos.*
