---
name: tweet-generator
description: >
  Generar hilos de Twitter/X sobre inversiones value investing. Usa esta skill
  cuando necesites crear tweets, hilos, o contenido para redes sociales sobre
  empresas, valoraciones, o noticias financieras. También aplica para mensajes
  del scheduler con tag [SCHEDULER] tweets.
---

# Tweet Generator — Hilos de inversión para Twitter/X

## Formato

- **Idioma**: español
- **Longitud**: máximo 280 caracteres por tweet
- **Hilos**: 5-8 tweets
- **Tono**: profesional pero cercano, como un analista que explica a su comunidad

## Estructura del hilo

### Tweet 1: Gancho
Dato impactante o pregunta provocadora. Incluir el ticker y emoji relevante.
Ejemplo: "🔍 $AMZN cotiza a $205 pero mi DCF dice que vale $256. ¿Oportunidad o trampa? Hilo 🧵"

### Tweets 2-3: Contexto del negocio
Qué hace la empresa, por qué es interesante, datos de revenue/crecimiento.
Usar números concretos, no generalidades.

### Tweets 4-5: Valoración / Noticia clave
Si es análisis: escenarios bear/base/bull con precios.
Si es noticia: qué pasó y por qué importa para el inversor.

### Tweet 6-7: Riesgos y matices
No ser solo alcista/bajista. Mostrar los dos lados. Credibilidad > hype.

### Tweet final: Conclusión + disclaimer
Recomendación resumida + "No es consejo de inversión. Haz tu propio análisis."

## Reglas

1. **Datos reales** — nunca inventar cifras. Si no tienes el dato, no lo pongas
2. **Sin hashtags excesivos** — máximo 2-3 por hilo, solo en el primer y último tweet
3. **Emojis con moderación** — 1-2 por tweet máximo, relevantes (📊💰🔍⚠️)
4. **No clickbait vacío** — el gancho debe tener sustancia
5. **Cifras redondas en tweets** — ok redondear ($205B en vez de $205,370M) para legibilidad

## Tipos de contenido

### Basado en análisis (datos del analyst)
Fuente: JSON de valoración. Incluir precio actual, fair value, margen de seguridad, 1-2 métricas clave.

### Basado en noticias (datos del news_fetcher)
Fuente: noticias RSS. Comentar la actualidad, no inventar datos financieros.
Conectar la noticia con implicaciones para la valoración.

### Basado en screener
Fuente: resultados del screener. "Las 3 empresas más infravaloradas esta semana según mi screener..."

## Para mensajes del scheduler

Los mensajes `[SCHEDULER]` de tweets incluyen: ticker, titular, resumen, score.
Generar el hilo basándose en esos datos. Si necesitas más contexto, leer el JSON
de valoración en `data/valuations/{TICKER}/` si existe.
