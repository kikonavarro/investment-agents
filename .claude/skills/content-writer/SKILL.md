---
name: content-writer
description: >
  Escribir artículos de inversión para Substack/blog. Usa esta skill cuando el usuario
  pida un artículo, post, análisis largo para publicar, o contenido editorial sobre
  inversiones. También aplica para "escribe sobre", "artículo de", "substack", "post".
---

# Content Writer — Artículos de inversión para Substack

## Parámetros por defecto

- **Idioma**: español
- **Extensión**: 1,500-2,500 palabras
- **Audiencia**: inversores retail con conocimientos intermedios

## Estructura

### 1. Gancho (1 párrafo)

El lector decide en 5 segundos si sigue leyendo. El gancho tiene que provocar una
reacción: curiosidad, sorpresa, o "espera, ¿qué?".

Técnicas que funcionan:

- **Dato contraintuitivo**: "Coca-Cola lleva 10 años sin crecer en volumen. Y sin embargo..."
- **Pregunta provocadora**: "¿Pagarías 45x beneficios por una empresa que no crece?"
- **Escenario concreto**: "Imagina que en 2019 hubieras comprado acciones de esta empresa desconocida..."
- **Contradicción**: "Todo el mundo dice que X es caro. Los números dicen otra cosa."

NUNCA empezar con "En este artículo vamos a..." ni "Hoy analizamos...".

### 2. Contexto (2-3 párrafos)

¿Por qué esta empresa/tema es relevante AHORA? ¿Qué está pasando en el mercado/sector?
Situar al lector antes de entrar en el análisis. Conectar con algo de actualidad cuando
sea posible.

### 3. Análisis con datos (cuerpo principal, 800-1200 palabras)

El corazón del artículo. Incluir:

- Datos financieros concretos (revenue, márgenes, FCF, crecimiento)
- Tablas cuando aporten claridad
- Comparaciones con competidores o medias del sector
- Gráficos descriptivos (describir tendencias aunque no puedas insertar imágenes)

Usar subtítulos para separar bloques temáticos.

Intercalar datos con interpretación — nunca más de 2 párrafos seguidos de
números sin explicar qué significan para el inversor.

### 4. Implicaciones para el inversor (2-3 párrafos)

¿Qué significa todo esto? ¿Es oportunidad o trampa? ¿A qué precio tiene sentido?
Aquí entra la valoración DCF resumida (no completa como en una tesis,
pero sí con escenarios bear/base/bull y fair value).

### 5. Conclusión (1-2 párrafos)

Resumir la tesis en 3-4 frases. Dar una opinión clara pero matizada.
Cerrar con: *"Este contenido es educativo. No es consejo de inversión."*

## Tipos de artículo

### Análisis de empresa individual

Fuente: JSON de valoración (`data/valuations/{TICKER}/`).
Si no existe, ejecutar `python main.py --analyst TICKER --data-only` primero.
Incluir DCF resumido con precios bear/base/bull.

### Artículo temático / sectorial

Fuente: datos de múltiples empresas, noticias, tendencias macro.
Ejemplo: "¿Es momento de comprar retailers?" → comparar 3-4 empresas del sector.

### Comentario de actualidad

Fuente: noticias recientes (RSS o datos del scheduler).
Conectar la noticia con implicaciones de valoración. No solo repetir la noticia.

### Resumen de screener / ideas de inversión

Fuente: resultados del screener.
"Las 5 empresas más infravaloradas esta semana" — formato ranking con mini-análisis.


**###** Ensayo de opinión / tesis propia
Fuente: idea proporcionada directamente por el usuario.
No requiere JSON ni datos del pipeline. El usuario aporta la tesis central
y opcionalmente datos de apoyo, enlaces, o notas sueltas.

Proceso:
**1.** El usuario describe su idea (puede ser un párrafo, bullet points, o notas desordenadas)
**2.** Proponer 3 ángulos para enfocar el artículo
**3.** Buscar datos de apoyo via web si el usuario no los aporta
**4.** Estructura más libre que el análisis de empresa — puede seguir la estructura
   base pero sin obligación de incluir DCF ni tablas comparativas
**5.** La voz del usuario importa más aquí — mantener sus expresiones y analogías
   si las ha dado

Ejemplos de temas:
**-** "Creo que los ETFs temáticos son una trampa para retail"
**-** "Mi experiencia comprando empresas aburridas en Europa"
**-** "Por qué sigo usando DCF cuando todo el mundo dice que no sirve"


## Reglas de contenido

1. **Datos reales** — todo número debe venir del JSON o de fuentes verificables
2. **No genérico** — cada artículo debe tener insights específicos, no obviedades
3. **Subtítulos** — usar `##` y `###` para estructura clara
4. **Tablas para comparar** — para datos comparativos, siempre más legible que prosa
5. **Citar fuentes** — "según el 10-K de 2025", "datos de Yahoo Finance"
6. **Una tesis clara** — no sentarse en la valla. Tener opinión.
7. **Cada párrafo se gana su sitio** — si no añade, se borra

## Integración con el pipeline

### Desde conversación directa

1. Ejecutar analyst si no hay datos recientes
2. Leer el JSON de valoración
3. Escribir el artículo siguiendo esta guía

### Desde Telegram bot

Si llega via check_inbox.py:

1. Mismos pasos que arriba
2. Responder via check_inbox.py respond
3. El bot divide en chunks de 4096 chars automáticamente

---
