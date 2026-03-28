import os
import re
import json
import gc
from google import genai
from google.genai import types
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception

# ── Model waterfall ────────────────────────────────────────────────────────────
# v1beta → supports response_mime_type (JSON mode)   → Gemini 2.0 models
# v1     → does NOT support response_mime_type        → Gemini 1.5 models
#
# Each entry: (api_version, model_id)
MODELS = [
    ("v1beta", "gemini-2.0-flash-lite"),
    ("v1beta", "gemini-2.0-flash"),
    ("v1",     "gemini-1.5-flash"),
    ("v1",     "gemini-1.5-flash-8b"),
    ("v1",     "gemini-1.5-pro"),
]


def _make_client(api_key, api_version):
    if api_version == "v1beta":
        return genai.Client(api_key=api_key)
    return genai.Client(api_key=api_key, http_options={"api_version": "v1"})


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


def _call_model(client, model_id, prompt, api_version, json_mode=True):
    """
    Call generate_content with or without JSON mode depending on api_version.
    v1beta supports response_mime_type; v1 does not.
    """
    if api_version == "v1beta" and json_mode:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
    else:
        # v1 API: no JSON mode — ask the model plainly and parse ourselves
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
        )
    return response


# ──────────────────────────────────────────────────────────────────────────────
def generate_questions(topic_name, count=10, language="English"):
    """
    Tries every model in the waterfall until one succeeds.
    Handles v1beta (JSON mode) and v1 (plain text + manual JSON parse).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment.")

    prompt = f"""
Generate exactly {count} multiple-choice questions about "{topic_name}" in {language}.
Return ONLY a valid JSON array with no extra text. Each element must have these exact keys:
"text", "option_a", "option_b", "option_c", "option_d", "correct_answer" (one of A/B/C/D), "explanation".
"""

    last_error = ""
    for api_version, model_id in MODELS:
        client = _make_client(api_key, api_version)
        try:
            print(f"Trying model: {model_id} (API: {api_version})")

            @retry(
                wait=wait_fixed(5),
                stop=stop_after_attempt(2),
                retry=retry_if_exception(
                    lambda e: _is_quota_error(e) and not _is_daily_quota_exhausted(e)
                ),
                reraise=True,
            )
            def _call():
                return _call_model(client, model_id, prompt, api_version)

            response = _call()
            data = _extract_json(response.text)
            gc.collect()
            print(f"Success with model: {model_id}")
            return data

        except Exception as e:
            last_error = str(e)
            print(f"Model {model_id} failed: {last_error[:150]}")
            continue

    gc.collect()
    if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
        return {"error": "Daily AI limit reached. Please try again tomorrow."}
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

    for api_version, model_id in MODELS:
        client = _make_client(api_key, api_version)
        try:
            response = _call_model(client, model_id, prompt, api_version)
            return _extract_json(response.text)
        except Exception as e:
            print(f"Model {model_id} failed (translate_question): {str(e)[:120]}")
            continue

    print("All translation models failed. Returning original.")
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

    for api_version, model_id in MODELS:
        client = _make_client(api_key, api_version)
        try:
            print(f"Translate-doc trying: {model_id} (API: {api_version})")
            # Document translation is always plain text — never JSON mode
            response = client.models.generate_content(model=model_id, contents=prompt)
            gc.collect()
            return response.text, was_truncated
        except Exception as e:
            print(f"Model {model_id} failed (translate_doc): {str(e)[:120]}")
            continue

    return "Daily AI limit reached. Please try again tomorrow.", was_truncated
