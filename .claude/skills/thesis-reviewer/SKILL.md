---
name: thesis-reviewer
description: >
  Revisión y comparación de tesis de inversión externas contra la nuestra.
  Usa esta skill cuando el usuario envíe un PDF, Excel o documento con una tesis
  de inversión de otra fuente y pida analizarla, compararla con la nuestra,
  o evaluar cuál es mejor. Detectar: "analiza esta tesis", "compara con tu tesis",
  "qué opinas de este análisis", "cuál es mejor", "review", "diferencias",
  archivo adjunto con tesis.
---

# Thesis Reviewer — Comparación con Tesis Externas

## Cuándo usar

- El usuario envía un PDF/Excel con una tesis de inversión de otro analista/casa
- Pide comparar los supuestos, metodología o conclusiones vs nuestra tesis
- Quiere saber si una tesis externa cambia nuestra visión

## Paso 0: Obtener los datos

1. **Leer la tesis externa**: si es PDF, usar `Read` tool. Si es Excel, usar openpyxl
2. **Leer nuestra tesis**: `data/valuations/{TICKER}/{TICKER}_tesis_inversion.md`
3. **Leer nuestro JSON**: `data/valuations/{TICKER}/{TICKER}_valuation.json`

Si nuestra tesis no existe para el ticker, ejecutar primero:
```bash
python main.py --analyst TICKER --data-only
```

## Marco de comparación (7 dimensiones)

### 1. Base de datos (¿de dónde salen los números?)
- ¿Usa datos reportados, pro-forma, ajustados?
- ¿Revenue base comparable? (si hay adquisiciones, ¿pro-forma o parcial?)
- ¿Cuántos años de histórico?
- **Veredicto**: ¿quién tiene la base de datos más completa/correcta?

### 2. Supuestos de crecimiento
- Revenue growth Y1-Y5: comparar lado a lado
- ¿Orgánico vs inorgánico? ¿Ajustado post-adquisición?
- ¿Consistente con el sector y la historia?
- **Veredicto**: ¿quién es más realista?

### 3. Márgenes y estructura de costes
- Gross margin, EBITDA margin, net margin
- ¿Usa EBITDA reportado, ajustado, ex-IFRS16?
- ¿Incluye/excluye elementos no recurrentes?
- **Veredicto**: ¿quién ajusta mejor?

### 4. Valoración y metodología
- DCF vs múltiplos vs otros métodos
- WACC: ¿cómo se calcula? ¿beta, risk-free, ERP?
- Terminal value: ¿múltiplo o Gordon Growth? ¿Sobre qué métrica?
- Escenarios: ¿cuántos? ¿cómo se ponderan?
- **Veredicto**: ¿quién tiene la metodología más sólida?

### 5. Balance y deuda
- ¿Cómo trata la deuda? ¿Total, neta, ajustada?
- Si hay banco cautivo, ¿lo detecta?
- ¿Considera shareholder loans, IFRS16, leases?
- **Veredicto**: ¿quién entiende mejor el balance?

### 6. Riesgos no capturados
- ¿Qué riesgos menciona la externa que nosotros no?
- ¿Qué riesgos mencionamos nosotros que la externa ignora?
- **Veredicto**: ¿quién tiene el mapa de riesgos más completo?

### 7. Información privilegiada / Calidad del research
- ¿Tiene acceso a management meetings, IR presentations?
- ¿Datos de segmentos no disponibles en Yahoo Finance?
- ¿Análisis de peers más profundo?
- **Veredicto**: ¿quién tiene mejor acceso a información?

## Estructura del output

```markdown
## Revisión: [Nombre de la casa/analista] vs Nuestra Tesis — [TICKER]

### Resumen de la comparación

| Aspecto | Tesis Externa | Nuestra Tesis |
|---------|--------------|---------------|
| Autor/Fuente | [Nombre] | Investment Agents |
| Fecha | [fecha] | [fecha] |
| Revenue base | EUR X.XXM | EUR X.XXM |
| EBITDA | EUR X.XXM | EUR X.XXM |
| Deuda neta | EUR X.XXM | EUR X.XXM |
| Precio objetivo (base) | EUR X.XX | EUR X.XX |
| Señal | [Comprar/Mantener/Vender] | [Comprar/Mantener/Vender] |
| Metodología | [DCF/Múltiplos/Otro] | DCF |

### Diferencias clave

#### 1. Base de datos — Mejor: [quién]
[2-3 frases]

#### 2. Supuestos de crecimiento — Mejor: [quién]
[2-3 frases]

#### 3. Márgenes — Mejor: [quién]
[2-3 frases]

#### 4. Valoración — Mejor: [quién]
[2-3 frases]

#### 5. Balance y deuda — Mejor: [quién]
[2-3 frases]

#### 6. Riesgos — Mejor: [quién]
[2-3 frases]

#### 7. Calidad del research — Mejor: [quién]
[2-3 frases]

### ¿Cambia nuestra visión?

[Párrafo honesto: ¿la tesis externa nos ha hecho cambiar de idea?
¿Debemos actualizar nuestros supuestos? ¿Qué aprendemos?]

### Veredicto

**Tesis mejor fundamentada: [quién]**
**Conclusión coincidente: [Sí/No]** — [1 frase explicando]
**Acción: [Actualizar nuestra tesis / Mantener nuestra tesis / Investigar más]**

---
*Revisión generada el [fecha]. No es consejo de inversión.*
```

## Guardar resultado

Guardar en `data/valuations/{TICKER}/review_{fuente}_{fecha}.md`

## Reglas

1. **Honestidad brutal** — si la tesis externa es mejor, decirlo claramente
2. **No defender por defender** — si nuestros datos son peores, reconocerlo
3. **Datos concretos** — cada diferencia debe citarse con números de ambas tesis
4. **Autocrítica constructiva** — si aprendemos algo, sugerir actualización de nuestra tesis
5. **Siempre declarar ganador** por dimensión, aunque sea por poco
