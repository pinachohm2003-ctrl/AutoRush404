"""
Busca en Pexels un vídeo relacionado con el tema y descarga la mejor
calidad disponible en formato vertical (o el más parecido).
"""
import os
import requests

from config import PEXELS_API_KEY, WORKDIR

HEADERS = {"Authorization": PEXELS_API_KEY}
SEARCH_URL = "https://api.pexels.com/videos/search"


def _pick_best_video_file(video):
    """De todos los renders disponibles de un vídeo, elige el vertical de
    mejor calidad; si no hay vertical, el de mayor resolución disponible."""
    files = video.get("video_files", [])
    portrait = [f for f in files if f.get("height", 0) > f.get("width", 0)]
    candidates = portrait if portrait else files
    # ordenamos por resolución descendente y cogemos uno "razonable" (no el 4K gigante)
    candidates = sorted(candidates, key=lambda f: f.get("height", 0), reverse=True)
    for f in candidates:
        if f.get("height", 0) <= 1920:
            return f
    return candidates[-1] if candidates else None


def fetch_clip(query, out_path=None, min_duration=8):
    out_path = out_path or os.path.join(WORKDIR, "clip.mp4")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    params = {
        "query": query,
        "orientation": "portrait",
        "per_page": 15,
        "size": "medium",
    }
    resp = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    videos = resp.json().get("videos", [])

    # si no hay resultados en vertical, reintentamos sin filtro de orientación
    if not videos:
        params.pop("orientation")
        resp = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])

    if not videos:
        raise RuntimeError(f"No se encontraron vídeos en Pexels para: {query}")

    # preferimos clips de duración razonable (ni 2s ni 5 minutos)
    videos = sorted(videos, key=lambda v: abs(v.get("duration", 0) - 15))

    chosen_file = None
    for video in videos:
        chosen_file = _pick_best_video_file(video)
        if chosen_file:
            break

    if not chosen_file:
        raise RuntimeError(f"No se pudo elegir un archivo de vídeo válido para: {query}")

    video_resp = requests.get(chosen_file["link"], stream=True, timeout=60)
    video_resp.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in video_resp.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)

    return out_path


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "ocean waves"
    path = fetch_clip(q)
    print("Clip descargado en:", path)
