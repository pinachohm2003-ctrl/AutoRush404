# Bot de Shorts de Curiosidades (100% automático y gratuito)

Genera, monta y publica 3 YouTube Shorts al día sobre curiosidades, sin
intervención manual y sin coste, usando GitHub Actions como "servidor".

## Cómo funciona

1. **Gemini** genera el tema, el guion, el título, la descripción y los
   hashtags (evitando repetir temas ya usados, guardados en `topics_used.json`).
2. **Pexels** aporta un clip de vídeo libre de derechos relacionado con el tema.
3. **edge-tts** narra el guion con una voz en español, gratis.
4. **moviepy + ffmpeg** montan el vídeo final en formato vertical 9:16, con
   título, subtítulos y música de fondo.
5. Se sube automáticamente a **YouTube** como Short (público).
6. Se envía una notificación de confirmación (o de error) a **Telegram**.
7. Cada domingo a las 22:00 se manda un **informe semanal** con vistas, likes,
   retención y el top 3 de la semana.

Todo el proceso corre en los servidores de GitHub Actions: no necesitas tener
tu ordenador encendido en ningún momento.

## Configuración inicial (una sola vez)

### 1. Subir este proyecto a tu repositorio

Sube todos estos archivos a tu repositorio de GitHub (el que ya creaste,
público, para tener minutos de Actions ilimitados).

### 2. Añadir tus claves como Secrets

En tu repositorio: **Settings → Secrets and variables → Actions → New
repository secret**. Crea uno por cada una de estas claves (con estos
nombres EXACTOS):

- `PEXELS_API_KEY`
- `GEMINI_API_KEY`
- `YT_CLIENT_ID`
- `YT_CLIENT_SECRET`
- `YT_REFRESH_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 3. Añadir música de fondo libre de derechos

Descarga 5-10 pistas cortas (loopables) de la [YouTube Audio Library]
(https://studio.youtube.com → Audio Library, sin copyright) y súbelas a la
carpeta `assets/music/` en formato `.mp3`. El bot elegirá una al azar en
cada vídeo.

### 4. (Opcional) Añadir una fuente personalizada

Si quieres una tipografía concreta para los textos del vídeo, sube un
archivo `.ttf` a `assets/fonts/font.ttf`. Si no lo haces, se usa una fuente
genérica del sistema.

### 5. Activar los workflows

Ve a la pestaña **Actions** de tu repositorio. Si GitHub te pregunta,
actívalos. Verás dos workflows: **"Publicar short"** (3 veces al día) y
**"Informe semanal"** (domingos).

Puedes lanzar cualquiera de los dos manualmente con el botón **"Run
workflow"**, para probar que todo funciona antes de esperar al horario
programado.

## Ajuste de horario en invierno

Los `cron` de los workflows están calculados para horario de verano español
(CEST, UTC+2). Cuando España cambie a horario de invierno (CET, UTC+1, hacia
finales de octubre), suma 1 hora a cada valor de `cron` en los dos archivos
`.github/workflows/*.yml` (por ejemplo, `0 6 * * *` pasaría a `0 7 * * *`).

## Escalar de 3 a 5 vídeos al día

Cuando quieras subir a 5 shorts/día, añade estas dos líneas dentro de
`schedule:` en `publish_short.yml`:

```yaml
- cron: "30 9 * * *"   # 11:30 hora española
- cron: "0 16 * * *"   # 18:00 hora española
```

## Límites gratuitos (referencia)

| Servicio | Límite gratis | Uso estimado (3 vídeos/día) |
|---|---|---|
| Pexels | 20.000 peticiones/mes | ~100/mes |
| Gemini (Flash) | 1.500 peticiones/día | ~3-6/día |
| edge-tts | Sin límite (no oficial) | — |
| YouTube Data API | 10.000 unidades/día | ~4.800/día (3 subidas) |
| GitHub Actions (repo público) | Ilimitado | — |
| Telegram | Sin límite | — |

⚠️ Hay un límite no documentado de subidas diarias en la API de YouTube que
en algunos proyectos nuevos se activa alrededor de 6-7 subidas/día. Por eso
se recomienda no superar 5 vídeos/día sin monitorizar antes cómo responde tu
proyecto concreto.

## Notas sobre las políticas de YouTube

Un canal 100% automatizado puede tener problemas de monetización si YouTube
lo detecta como "contenido masivo/repetitivo" sin valor añadido. Para
reducir ese riesgo: varía el estilo de los guiones, revisa manualmente los
primeros vídeos, y considera añadir de vez en cuando algún toque editorial
propio (un texto de cierre, una pregunta a la audiencia, etc.).
