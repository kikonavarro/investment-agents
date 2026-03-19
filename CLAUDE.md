# Investment Agents — Instrucciones para Claude Code

## Principio clave
Python hace el trabajo pesado (datos, cálculos, Excel, filtros). Claude Code hace la interpretación y escritura (sin coste API adicional, usa tu suscripción Max).

## Pipeline de inversión (modo sin API)

Cuando el usuario pida análisis, tesis, screener, tweets o artículos, usa el flag `--data-only` para ejecutar solo el Python y luego haz la interpretación tú mismo.

### 1. Valoración completa (analyst)
```bash
python main.py --analyst TICKER --data-only
```
- Genera: `data/valuations/{TICKER}/{TICKER}_valuation.json` + Excel DCF + SEC filings
- Ya es 100% Python, no usa API ni con ni sin `--data-only`
- Lee el JSON generado para ver los resultados

### 2. Tesis de inversión
```bash
python main.py --analyst TICKER --data-only
```
Luego lee `data/valuations/{TICKER}/{TICKER}_valuation.json` y escribe la tesis tú mismo siguiendo el prompt de `config/prompts.py` → `THESIS_WRITER`. Guarda el resultado en:
- `data/valuations/{TICKER}/{TICKER}_tesis_inversion.md`

### 3. Screener (buscar ideas value)
```bash
python main.py --screener graham_default --data-only
```
- Devuelve top 15 candidatos con métricas cuantitativas
- Haz el ranking cualitativo tú mismo (evalúa moat, calidad del negocio, riesgos)
- Filtros disponibles: `graham_default`, `value_aggressive`, `bargain_hunter`

### 4. Tweets
Ejecuta analyst o news_fetcher con `--data-only`, lee los datos, y genera el hilo de tweets tú mismo siguiendo el prompt `SOCIAL_MEDIA` de `config/prompts.py`.

### 5. Artículo Substack
Lee los datos disponibles y escribe el artículo siguiendo el prompt `CONTENT_WRITER` de `config/prompts.py`.

### 6. Portfolio tracker
El portfolio tracker **siempre usa la API** (necesita automatización):
```bash
python main.py --portfolio status
```

## Estructura de archivos clave
- `config/prompts.py` — todos los system prompts (referencia para escribir tesis/tweets/artículos)
- `config/settings.py` — modelos, rutas, configuración
- `config/screener_filters.yaml` — filtros cuantitativos del screener
- `data/valuations/{TICKER}/` — output del analyst (JSON + Excel + SEC)
- `tools/` — módulos Python puros (sin LLM)

## Tickers internacionales
- España: añadir `.MC` (ej: TEF.MC, ITX.MC, SAN.MC)
- Otros mercados europeos: consultar sufijo Yahoo Finance
- USA: ticker directo (AAPL, MSFT, etc.)
