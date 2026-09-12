"""
Genera el contenido del short a partir de temas de psicologia y comportamiento
humano, con hook fuerte, tension y payoff, evitando repetir hechos ya usados
recientemente.
"""
import json
import os
import re
import time
import unicodedata
import difflib
from datetime import datetime, timedelta

from google import genai
from google.genai import errors as genai_errors

from config import GEMINI_API_KEY, TOPICS_FILE

client = genai.Client(api_key=GEMINI_API_KEY)

DIAS_ENFRIAMIENTO = 30
UMBRAL_SIMILITUD = 0.55

_PROMPT_LINEAS = [
    "You are an expert viral scriptwriter for YouTube Shorts about psychology",
    "and human behavior, creating content for young viewers used to fast,",
    "surprising short-form content. Your topics cover: cognitive biases, body",
    "language, social psychology, habits, persuasion, relationships, and",
    "everyday human behavior explained through real psychological research.",
    "",
    "OPENING (first sentence): create instant curiosity with something",
    "unexpected about human behavior, stated as a bold or unsettling claim.",
    "This must stop the scroll immediately. Never start with 'Did you know'",
    "or 'Here's a fact' - these are overused and cause viewers to swipe away.",
    "",
    "STRUCTURE: Hook -> build tension around ONE clear psychological effect",
    "or discovery -> reveal the surprising mechanism behind it -> payoff",
    "(why this matters or how it applies to the viewer's own life).",
    "",
    "EMOTION: the script must move through curiosity, then tension, then a",
    "satisfying payoff when the mechanism is revealed. Never end flatly on",
    "the fact alone.",
    "",
    "PACING: short sentences, one idea per sentence, no filler words, high",
    "energy, fast rhythm.",
    "",
    "CLOSING LINE: end with a strong, quotable closing line, followed by a",
    "subtle call to action such as inviting the viewer to think about their",
    "own behavior or follow for more.",
    "",
    "QUALITY BAR: avoid overused psychology facts that are already extremely",
    "common in short-form content, such as smiling making you happier or the",
    "brain not telling the difference between real and imagined. Prioritize",
    "specific, lesser-known findings with a named effect, bias, or study",
    "concept when possible, such as anchoring bias, mere-exposure effect,",
    "bystander effect, mirroring, or primacy effect.",
    "",
    "Always return ONLY a valid JSON object, no markdown, no backticks, no",
    "extra text, with exactly these keys:",
    "",
    "{",
    '  "topic": "2-4 word summary of the topic",',
    '  "title": "title in English, max 60 characters, intriguing hook, no',
    'quotation marks",',
    '  "script": "script in English, 65-90 words, following the structure',
    'above, ready to be narrated aloud in about 28-32 seconds",',
    '  "description": "YouTube description, 2-3 sentences, in English, ending',
    'with a short call to action",',
    '  "hashtags": ["#shorts", "#psychology", "#humanbehavior", "#tag4",',
    '"#tag5"],',
    '  "pexels_query": "2-4 words describing a generic image or video related',
    'to the topic, such as people talking, office meeting, crowd walking,',
    'couple arguing, person thinking"',
    "}",
    "",
    "Rules:",
    "- The script must be speakable in about 30 seconds, no more than 90 words.",
    "- Do not repeat any of the topics already used that are passed to you, nor",
    "anything very similar even if labeled differently.",
    "- The pexels_query must describe something generic and easy to find in a",
    "stock footage library, not something too specific.",
]
SYSTEM_PROMPT = "\n".join(_PROMPT_LINEAS)


def _normalizar(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def _load_used_topics():
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_used_topic(topic, script):
    used = _load_used_topics()
    used.append({
        "topic": topic,
        "script": script,
        "date": datetime.utcnow().isoformat(),
    })
    used = used[-200:]
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(used, f, ensure_ascii=False, indent=2)


def _entradas_en_enfriamiento(dias=DIAS_ENFRIAMIENTO):
    used = _load_used_topics()
    limite = datetime.utcnow() - timedelta(days=dias)
    recientes = []
    for t in used:
        try:
            fecha = datetime.fromisoformat(t["date"])
        except (KeyError, ValueError):
            fecha = datetime.utcnow()
        if fecha >= limite:
            recientes.append(t)
    return recientes


def _es_repetido(nuevo_topic, nuevo_script, recientes):
    topic_norm = _normalizar(nuevo_topic)
    script_norm = _normalizar(nuevo_script)

    for entrada in recientes:
        topic_previo = _normalizar(entrada.get("topic", ""))
        script_previo = _normalizar(entrada.get("script", ""))

        if topic_norm == topic_previo:
            return True

        ratio = difflib.SequenceMatcher(None, script_norm, script_previo).ratio()
        if ratio >= UMBRAL_SIMILITUD:
            return True

    return False


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE)
    return json.loads(text)


def _call_gemini(user_prompt, temperature=1.0):
    max_retries = 3
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return client.models.generate_content(
                model="gemini-3.6-flash",
                contents=user_prompt,
                config={"system_instruction": SYSTEM_PROMPT, "temperature": temperature},
            )
        except genai_errors.ServerError as e:
            last_error = e
            wait = 15 * attempt
            print("Gemini overloaded (attempt " + str(attempt) + "/" + str(max_retries) + "), retrying in " + str(wait) + "s...")
            time.sleep(wait)
    raise last_error


def generate_content():
    recientes = _entradas_en_enfriamiento()
    used_topics_str = ", ".join(t["topic"] for t in recientes[-40:]) or "none yet"

    max_intentos_tema = 4
    data = None

    for intento in range(1, max_intentos_tema + 1):
        user_prompt = (
            "Topics already used recently (do NOT repeat these, or anything "
            "very similar): " + used_topics_str + "\n\nGenerate a new short."
        )
        response = _call_gemini(user_prompt, temperature=1.0 + intento * 0.15)
        data = _extract_json(response.text)

        if not _es_repetido(data["topic"], data["script"], recientes):
            _save_used_topic(data["topic"], data["script"])
            return data

        print("Topic repeated or too similar ('" + data["topic"] + "'), retrying (" + str(intento) + "/" + str(max_intentos_tema) + ")...")

    data["topic"] = data["topic"] + " (variant " + str(len(recientes) + 1) + ")"
    print("Forcing a variant after exhausting retries: " + data["topic"])
    _save_used_topic(data["topic"], data["script"])
    return data


if __name__ == "__main__":
    content = generate_content()
    print(json.dumps(content, ensure_ascii=False, indent=2))
