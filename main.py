"""
Punto de entrada. Ejecuta el pipeline completo para UN short de psicologia:
1. Genera tema, guion, titulo y hashtags (Gemini)
2. Descarga clip de video libre de derechos (Pexels)
3. Genera la voz narrada
4. Monta el video final (moviepy)
5. Sube a YouTube Shorts
6. Notifica por Telegram

Este script lo dispara GitHub Actions varias veces al dia.
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))

from config import WORKDIR  # noqa: E402
from generate_content import generate_content  # noqa: E402
from fetch_clip import fetch_clip  # noqa: E402
from generate_voice import generate_voice  # noqa: E402
from build_video import build_video  # noqa: E402
from upload_youtube import upload_short  # noqa: E402
from telegram_notify import send_telegram_message  # noqa: E402


def run():
    os.makedirs(WORKDIR, exist_ok=True)

    print("1/5 Generating script, title and hashtags with Gemini...")
    content = generate_content()
    print("   Topic:", content["topic"])
    print("   Title:", content["title"])

    print("2/5 Downloading clip from Pexels...")
    clip_path = fetch_clip(content["pexels_query"])

    print("3/5 Generating narrated voice...")
    voice_path = generate_voice(content["script"])

    print("4/5 Building the final video...")
    video_path = build_video(
        clip_path=clip_path,
        voice_path=voice_path,
        title=content["title"],
        script_text=content["script"],
    )

    print("5/5 Uploading to YouTube...")
    url = upload_short(
        video_path=video_path,
        title=content["title"],
        description=content["description"],
        hashtags=content["hashtags"],
    )

    print("Uploaded successfully:", url)

    try:
        send_telegram_message(
            f"✅ <b>New short published</b>\n\n"
            f"📌 {content['title']}\n"
            f"🔗 {url}\n"
            f"🏷️ {' '.join(content['hashtags'])}"
        )
    except Exception as e:
        print(f"⚠️ Warning: could not notify via Telegram ({e}). The video was uploaded successfully.")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        error_text = f"❌ <b>Error generating the short</b>\n\n{type(e).__name__}: {e}"
        print(error_text)
        traceback.print_exc()
        try:
            send_telegram_message(error_text)
        except Exception:
            pass
        sys.exit(1)
