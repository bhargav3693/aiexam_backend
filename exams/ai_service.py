import os
import re
import json
import gc
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception

# Load environment variables (crucial for local testing)
load_dotenv()

# ── Model Configuration ─────────────────────────────────────────────────────────
# Hardcoded to EXACTLY one model as requested.
# Using 'gemini-2.0-flash' strictly, as it is supported and returns 429 instead of 404.
MODEL_ID = "gemini-2.0-flash"
USE_MOCK_DATA = True  # Set to False to re-enable live AI generation

def _make_client(api_key):
    # Let the SDK handle the version automatically
    return genai.Client(api_key=api_key)


def _is_quota_error(e: Exception) -> bool:
    s = str(e)
    return "429" in s or "RESOURCE_EXHAUSTED" in s


def _is_daily_quota_exhausted(e: Exception) -> bool:
    s = str(e)
    return "PerDay" in s or "limit: 0" in s


def _extract_json(text: str):
    """
    Robustly pull a JSON value out of a model response.
    Handles markdown code fences (```json ... ```) and bare JSON.
    """
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    return json.loads(text)


def _call_model(client, prompt):
    """Call generate_content with the single hardcoded model."""
    return client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
    )


# ──────────────────────────────────────────────────────────────────────────────
def generate_questions(topic_name, count=10, language="English"):
    """
    Generates multiple-choice questions using the assigned Gemini model.
    """
    if USE_MOCK_DATA:
        print(f"DEBUG: BYPASSING AI - Returning MOCK data for '{topic_name}'", flush=True)
        mock_questions = [
            {
                "text": "What is the speed of light in a vacuum?",
                "option_a": "300,000 km/s",
                "option_b": "150,000 km/s",
                "option_c": "1,000,000 km/s",
                "option_d": "30,000 km/s",
                "correct_answer": "A",
                "explanation": "The speed of light is approximately 299,792 kilometers per second."
            },
            {
                "text": "Which planet is known as the Red Planet?",
                "option_a": "Venus",
                "option_b": "Jupiter",
                "option_c": "Mars",
                "option_d": "Saturn",
                "correct_answer": "C",
                "explanation": "Mars is often called the 'Red Planet' due to the iron oxide on its surface."
            },
            {
                "text": "What is the powerhouse of the cell?",
                "option_a": "Nucleus",
                "option_b": "Ribosome",
                "option_c": "Mitochondria",
                "option_d": "Endoplasmic Reticulum",
                "correct_answer": "C",
                "explanation": "Mitochondria act as the powerhouse of the cell by generating ATP."
            },
            {
                "text": "What is the chemical symbol for Gold?",
                "option_a": "Ag",
                "option_b": "Au",
                "option_c": "Pb",
                "option_d": "Fe",
                "correct_answer": "B",
                "explanation": "The symbol 'Au' comes from the Latin word for gold, 'aurum'."
            },
            {
                "text": "What is the value of Pi rounded to two decimal places?",
                "option_a": "3.12",
                "option_b": "3.16",
                "option_c": "3.14",
                "option_d": "3.18",
                "correct_answer": "C",
                "explanation": "Pi is a mathematical constant approximately equal to 3.14."
            }
        ]
        return mock_questions[:count]

    keys_env = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
    if not keys_env:
        raise ValueError("GEMINI_API_KEYS is not set in environment.")
    api_keys = [k.strip() for k in keys_env.split(",") if k.strip()]

    print(f"DEBUG: generate_questions loaded {len(api_keys)} keys.", flush=True)
    for i, k in enumerate(api_keys):
        print(f"  -> Key {i+1} starts with: {k[:4]}... ends with: ...{k[-4:]}", flush=True)

    prompt = f"""
Generate exactly {count} multiple-choice questions about "{topic_name}" in {language}.
Return ONLY a valid JSON array with no extra text. Each element must have these exact keys:
"text", "option_a", "option_b", "option_c", "option_d", "correct_answer" (one of A/B/C/D), "explanation".
"""

    last_error = ""
    for idx, api_key in enumerate(api_keys):
        client = _make_client(api_key)
        try:
            response = _call_model(client, prompt)
            data = _extract_json(response.text)
            gc.collect()
            return data
        except Exception as e:
            last_error = str(e)
            if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
                print(f"generate_questions: Key {idx+1} exhausted. Waiting 2 seconds then trying next key...")
                time.sleep(2)
                continue
            raise Exception(f"AI Generation failed: {last_error}")

    raise Exception("AI Limit Reached on all available keys. Please wait and try again.")


# ──────────────────────────────────────────────────────────────────────────────
def translate_question_data(question_data, target_language):
    """Translates a question dict. Falls back to original on failure."""
    keys_env = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
    if not keys_env:
        raise ValueError("GEMINI_API_KEYS is not set.")
    api_keys = [k.strip() for k in keys_env.split(",") if k.strip()]

    prompt = f"""
Translate the following question and options into {target_language}.
Return ONLY a valid JSON object with the exact same keys: 'text', 'option_a', 'option_b', 'option_c', 'option_d'.

Input JSON:
{json.dumps(question_data)}
"""

    last_error = ""
    for idx, api_key in enumerate(api_keys):
        client = _make_client(api_key)
        try:
            response = _call_model(client, prompt)
            return _extract_json(response.text)
        except Exception as e:
            last_error = str(e)
            if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
                print(f"translate_question: Key {idx+1} exhausted. Waiting 2 seconds then trying next key...")
                time.sleep(2)
                continue
            print(f"Translation failed: {last_error[:120]}")
            return question_data

    raise Exception("AI Limit Reached on all available keys. Please wait and try again.")


# ──────────────────────────────────────────────────────────────────────────────
def translate_document(text, target_language):
    """Translates a plain text document. Returns (translated_text, was_truncated)."""
    keys_env = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
    if not keys_env:
        raise ValueError("GEMINI_API_KEYS is not set.")
    api_keys = [k.strip() for k in keys_env.split(",") if k.strip()]

    was_truncated = False
    if len(text) > 2000:
        text = text[:2000]
        was_truncated = True

    gc.collect()

    prompt = f"""
Translate the following text into {target_language}.
Provide a bilingual line-by-line interleaved format: original line, then translated line, alternating.

{text}
"""
    del text
    gc.collect()

    last_error = ""
    for idx, api_key in enumerate(api_keys):
        client = _make_client(api_key)
        try:
            response = _call_model(client, prompt)
            gc.collect()
            return response.text, was_truncated
        except Exception as e:
            last_error = str(e)
            if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
                print(f"translate_document: Key {idx+1} exhausted. Waiting 2 seconds then trying next key...")
                time.sleep(2)
                continue
            return "Daily AI limit reached. Please try again tomorrow.", was_truncated

    raise Exception("AI Limit Reached on all available keys. Please wait and try again.")
