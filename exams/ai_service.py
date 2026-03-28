import os
import re
import json
import gc
from google import genai
from google.genai import types
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception

# ── Model Configuration ─────────────────────────────────────────────────────────
# Hardcoded to EXACTLY one model as requested.
# Using 'gemini-2.0-flash' strictly, as it is supported and returns 429 instead of 404.
MODEL_ID = "gemini-2.0-flash"

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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment.")

    prompt = f"""
Generate exactly {count} multiple-choice questions about "{topic_name}" in {language}.
Return ONLY a valid JSON array with no extra text. Each element must have these exact keys:
"text", "option_a", "option_b", "option_c", "option_d", "correct_answer" (one of A/B/C/D), "explanation".
"""

    client = _make_client(api_key)
    try:
        response = _call_model(client, prompt)
        data = _extract_json(response.text)
        gc.collect()
        return data
    except Exception as e:
        last_error = str(e)
        if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
            raise Exception("AI Limit Reached. Please wait and try again.")
        raise Exception(f"AI Generation failed: {last_error}")


# ──────────────────────────────────────────────────────────────────────────────
def translate_question_data(question_data, target_language):
    """Translates a question dict. Falls back to original on failure."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    prompt = f"""
Translate the following question and options into {target_language}.
Return ONLY a valid JSON object with the exact same keys: 'text', 'option_a', 'option_b', 'option_c', 'option_d'.

Input JSON:
{json.dumps(question_data)}
"""

    client = _make_client(api_key)
    try:
        response = _call_model(client, prompt)
        return _extract_json(response.text)
    except Exception as e:
        last_error = str(e)
        if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
            raise Exception("AI Limit Reached. Please wait and try again.")
        print(f"Translation failed: {last_error[:120]}")
        return question_data


# ──────────────────────────────────────────────────────────────────────────────
def translate_document(text, target_language):
    """Translates a plain text document. Returns (translated_text, was_truncated)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

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

    client = _make_client(api_key)
    try:
        response = _call_model(client, prompt)
        gc.collect()
        return response.text, was_truncated
    except Exception as e:
        last_error = str(e)
        if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
            raise Exception("AI Limit Reached. Please wait and try again.")
        return "Daily AI limit reached. Please try again tomorrow.", was_truncated
