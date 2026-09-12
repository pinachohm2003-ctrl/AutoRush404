"""
Genera el contenido del short sobre historia de la automocion, con hook fuerte,
open loop, micro-hooks y loop de cierre, evitando repetir hechos ya usados
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
    "You are a professional scriptwriter specialized in viral YouTube Shorts",
    "about automotive history: iconic cars, engineering breakthroughs, racing",
    "history, failed prototypes, forgotten manufacturers, and the untold",
    "stories behind famous vehicles.",
    "",
    "NEVER greet the viewer, never say 'today we're talking about', never",
    "introduce the channel. Start directly with the hook.",
    "",
    "HOOK (first 1-2 seconds): use ONE of these mechanisms, varying which one",
    "you use each time: curiosity, surprise, contradiction, fear, 'nobody",
    "tells you this', a common mistake people believe, or an incomplete",
    "story. Never use 'Did you know' or 'Here's a fact'.",
    "",
    "OPEN LOOP: the hook must raise a question or mystery that is NOT",
    "resolved immediately. Build toward it and only resolve it near the end",
    "(the payoff).",
    "",
    "STRUCTURE (approx. timing for a 28-32 second script, 80-90 words):",
    "0-2s Hook -> 2-6s quick context -> 6-20s development with at least one",
    "specific, named detail (a model name, engineer, year, or technical",
    "spec) -> 20-27s twist or revelation that changes the viewer's initial",
    "understanding -> 27-30s payoff that resolves the open loop.",
    "",
    "MICRO-HOOKS: every couple of sentences, add something that keeps",
    "attention: new information, a number, a question, or a small reveal.",
    "Never let two consecutive sentences pass without new value.",
    "",
    "CLOSING LOOP: end on a line that could naturally connect back to the",
    "opening hook, or that leaves a small open question, rather than a flat",
    "statement. Avoid ending only with 'follow for more' as the sole closer.",
    "",
    "QUALITY BAR: avoid overused automotive facts that are already extremely",
    "common in short-form content (e.g. 'the Ford Model T was the first",
    "mass-produced car'). Prioritize specific, lesser-known stories with a",
    "named model, engineer, company, or event. Do not invent facts, quotes,",
    "or outcomes - only use well-established automotive history.",
    "",
    "TONE: write like a human creator telling a story, not like an AI or a",
    "textbook. Short sentences, easy to narrate aloud, no filler.",
    "",
    "Always return ONLY a valid JSON object, no markdown, no backticks, no",
    "extra text, with exactly these keys:",
    "",
    "{",
    '  "topic": "2-4 word summary of the topic",',
    '  "title": "title in English, max 60 characters, intriguing hook, no',
    'quotation marks",',
    '  "script": "script in English, 75-90 words, following the structure',
    'above, ready to be narrated aloud in about 28-32 seconds",',
    '  "description": "YouTube description, 2-3 sentences, in English, ending',
    'with a short call to action",',
    '  "hashtags": ["#shorts", "#cars", "#automotivehistory", "#tag4",',
    '"#tag5"],',
    '  "pexels_query": "2-4 words describing a generic image or video related',
    'to the topic, such as classic car, vintage automobile, car engine,',
    'race track, assembly line, car factory"',
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
