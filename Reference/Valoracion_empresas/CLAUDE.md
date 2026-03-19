# Sistema Automatizado de Valoración de Empresas

## Descripción
Herramienta que automatiza la valoración de cualquier empresa pública de EEUU.
Al recibir un ticker, genera: descarga de 10-K (SEC), modelo de valoración en Excel (DCF con 3 escenarios), y PDF con tesis de inversión.

## Estructura
```
valorar_empresa.py          # Script principal - orquestador
sec_downloader.py           # Descarga 10-K filings de SEC EDGAR
financial_data.py           # Datos financieros vía yfinance + SEC XBRL
excel_generator.py          # Genera Excel de valoración (replica modelo Netflix)
pdf_generator.py            # Genera PDF con tesis de inversión
news_fetcher.py             # Busca noticias recientes de la empresa
```

## Output por empresa
```
{ticker}/
├── SEC_filings/            # 10-K filings descargados
├── {ticker}_modelo_valoracion.xlsx
└── {ticker}_tesis_inversion.pdf
```

## Uso
```bash
python3 valorar_empresa.py AAPL
```

## Dependencias
- openpyxl, requests, beautifulsoup4, matplotlib, seaborn (preinstaladas)
- fpdf2 (generación PDF)
- yfinance (datos financieros gratuitos)

## Convenciones
- Solo fuentes gratuitas (sin API keys)
- Excel con fórmulas reales (no valores hardcodeados)
- 3 escenarios: Base (1), Bull (2), Bear (3)
- Colores: Headers FF273A4F (azul oscuro), Inputs FFB2C3BC (verde claro), Editables fuente azul FF0000FF
- Revenue desglosado por segmentos de negocio
- DCF con WACC + Terminal Value Multiple + tabla de sensibilidad
