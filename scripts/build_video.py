"""
Monta el short final combinando:
- el clip de fondo (recortado/loopeado a 9:16 y a la duración de la voz)
- la voz narrada
- música de fondo a bajo volumen
- el título y el guion troceado como subtítulos en pantalla

Requiere ffmpeg instalado en el sistema (en GitHub Actions se instala en el workflow).
"""
import os
import random
import textwrap

from PIL import Image

# Pillow >=10 eliminó Image.ANTIALIAS (ahora se llama Image.LANCZOS), pero
# moviepy 1.0.3 todavía lo usa internamente. Este parche restaura el alias
# sin tener que bajar la versión de Pillow (que google-genai necesita >=10).
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    afx,
    vfx,
)

from config import FONT_PATH, MUSIC_DIR, MUSIC_VOLUME, VIDEO_HEIGHT, VIDEO_WIDTH, WORKDIR


def _fit_to_vertical(clip, width=VIDEO_WIDTH, height=VIDEO_HEIGHT):
    """Recorta y escala el clip para que llene un frame vertical 9:16."""
    target_ratio = width / height
    clip_ratio = clip.w / clip.h

    if clip_ratio > target_ratio:
        # el clip es más ancho de lo necesario -> recortamos los laterales
        new_width = int(clip.h * target_ratio)
        x1 = (clip.w - new_width) // 2
        clip = clip.crop(x1=x1, x2=x1 + new_width)
    else:
        # el clip es más alto de lo necesario -> recortamos arriba/abajo
        new_height = int(clip.w / target_ratio)
        y1 = (clip.h - new_height) // 2
        clip = clip.crop(y1=y1, y2=y1 + new_height)

    return clip.resize((width, height))


def _loop_to_duration(clip, duration):
    if clip.duration >= duration:
        return clip.subclip(0, duration)
    return clip.fx(vfx.loop, duration=duration)


def _make_caption_clips(script_text, duration, width=VIDEO_WIDTH):
    """Trocea el guion en 4-6 frases cortas y las muestra repartidas en el tiempo,
    tipo subtítulo, en la parte inferior del vídeo."""
    words = script_text.split()
    chunk_size = max(4, len(words) // 6)
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    chunks = [c for c in chunks if c.strip()]

    per_chunk = duration / len(chunks)
    clips = []
    t = 0
    for chunk in chunks:
        wrapped = "\n".join(textwrap.wrap(chunk, width=28))
        txt = (
            TextClip(
                wrapped,
                fontsize=64,
                color="white",
                font=FONT_PATH if os.path.exists(FONT_PATH) else "DejaVu-Sans-Bold",
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(width - 120, None),
                align="center",
            )
            .set_start(t)
            .set_duration(per_chunk)
            .set_position(("center", 0.72), relative=True)
        )
        clips.append(txt)
        t += per_chunk
    return clips


def _make_title_clip(title, duration, width=VIDEO_WIDTH):
    wrapped = "\n".join(textwrap.wrap(title, width=22))
    return (
        TextClip(
            wrapped,
            fontsize=72,
            color="yellow",
            font=FONT_PATH if os.path.exists(FONT_PATH) else "DejaVu-Sans-Bold",
            stroke_color="black",
            stroke_width=4,
            method="caption",
            size=(width - 100, None),
            align="center",
        )
        .set_start(0)
        .set_duration(min(4, duration))
        .set_position(("center", 0.08), relative=True)
    )


def _pick_music_track():
    if not os.path.isdir(MUSIC_DIR):
        return None
    tracks = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith((".mp3", ".wav", ".m4a"))]
    if not tracks:
        return None
    return os.path.join(MUSIC_DIR, random.choice(tracks))


def build_video(clip_path, voice_path, title, script_text, out_path=None):
    out_path = out_path or os.path.join(WORKDIR, "final_video.mp4")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    voice_audio = AudioFileClip(voice_path)
    duration = voice_audio.duration + 0.8  # pequeño margen al final

    base_clip = VideoFileClip(clip_path)
    base_clip = _fit_to_vertical(base_clip)
    base_clip = _loop_to_duration(base_clip, duration).without_audio()

    audio_tracks = [voice_audio.set_start(0.3)]
    music_path = _pick_music_track()
    if music_path:
        music = AudioFileClip(music_path)
        music = music.fx(afx.audio_loop, duration=duration) if music.duration < duration else music.subclip(0, duration)
        music = music.fx(afx.volumex, MUSIC_VOLUME)
        audio_tracks.append(music)

    final_audio = CompositeAudioClip(audio_tracks)

    overlays = [_make_title_clip(title, duration)]
    overlays += _make_caption_clips(script_text, duration)

    final = CompositeVideoClip([base_clip, *overlays], size=(VIDEO_WIDTH, VIDEO_HEIGHT))
    final = final.set_audio(final_audio).set_duration(duration)

    final.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        temp_audiofile=os.path.join(WORKDIR, "temp-audio.m4a"),
        remove_temp=True,
        logger=None,
    )

    return out_path


if __name__ == "__main__":
    import sys
    build_video(sys.argv[1], sys.argv[2], "Título de prueba", "Este es un guion de prueba para el vídeo.")
