"""
Configuración central del bot.
Todas las claves se leen de variables de entorno (nunca hardcodeadas),
que en producción vienen de los Secrets de GitHub Actions.
"""
import os

# --- APIs de contenido ---
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"].strip()
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()

# --- YouTube OAuth ---
YT_CLIENT_ID = os.environ["YT_CLIENT_ID"].strip()
YT_CLIENT_SECRET = os.environ["YT_CLIENT_SECRET"].strip()
YT_REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN"].strip()

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"].strip()

# --- Parámetros del vídeo ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
TARGET_DURATION = 30  # segundos aprox. de cada short
MUSIC_VOLUME = 0.12  # volumen relativo de la música de fondo frente a la voz

# --- Voz (Piper, motor local, sin llamadas a servidores externos) ---
PIPER_VOICE_NAME = "en_US-lessac-medium"

# --- Rutas ---
# Correcto para tu estructura real (config.py está en scripts/):
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
FONT_PATH = os.path.join(ASSETS_DIR, "fonts", "font.ttf")
WORKDIR = os.path.join(BASE_DIR, "workdir")
TOPICS_FILE = os.path.join(BASE_DIR, "topics_used.json")
VOICES_DIR = os.path.join(BASE_DIR, "voices")
PIPER_MODEL_PATH = os.path.join(VOICES_DIR, f"{PIPER_VOICE_NAME}.onnx")
