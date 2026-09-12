"""
Convierte el guion en audio narrado usando Piper TTS.

A diferencia de edge-tts, Piper es un motor de voz que corre 100% en local:
no se conecta a ningún servidor externo, así que no puede ser bloqueado por
IP (el problema que sí tenía edge-tts en GitHub Actions). El modelo de voz
(.onnx) se descarga una vez en el propio workflow, antes de llamar a esta
función.
"""
import os
import subprocess

from config import PIPER_MODEL_PATH, WORKDIR


def generate_voice(script_text, out_path=None):
    out_path = out_path or os.path.join(WORKDIR, "voice.wav")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if not os.path.exists(PIPER_MODEL_PATH):
        raise FileNotFoundError(
            f"No se encuentra el modelo de voz de Piper en {PIPER_MODEL_PATH}. "
            "Revisa el paso 'Descargar el modelo de voz' del workflow."
        )

    result = subprocess.run(
        ["piper", "--model", PIPER_MODEL_PATH, "--output_file", out_path],
        input=script_text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Error generando voz con Piper: {result.stderr.decode(errors='ignore')}")

    return out_path


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "Esto es una prueba de voz."
    path = generate_voice(text)
    print("Audio generado en:", path)
