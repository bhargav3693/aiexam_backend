import os
import json
import gc
from google import genai
from google.genai import types
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception

# ── Model waterfall ────────────────────────────────────────────────────────────
# The new google-genai SDK defaults to v1beta.
# Gemini 2.0 models  → v1beta  ✅
# Gemini 1.5 models  → v1      ✅  (they return 404 on v1beta!)
#
# Strategy: two clients, tried in order.
# (client, model_id)
def _build_model_list(api_key):
    client_beta = genai.Client(api_key=api_key)                                          # v1beta – 2.0 models
    client_v1   = genai.Client(api_key=api_key, http_options={"api_version": "v1"})     # v1     – 1.5 models
    return [
        (client_beta, "gemini-2.0-flash-lite"),
        (client_beta, "gemini-2.0-flash"),
        (client_v1,   "gemini-1.5-flash"),
        (client_v1,   "gemini-1.5-flash-8b"),
        (client_v1,   "gemini-1.5-pro"),
    ]


def _is_quota_error(e: Exception) -> bool:
    s = str(e)
    return "429" in s or "RESOURCE_EXHAUSTED" in s


def _is_daily_quota_exhausted(e: Exception) -> bool:
    """Daily limits can't be fixed by waiting — skip to next model immediately."""
    s = str(e)
    return "PerDay" in s or "limit: 0" in s


# ──────────────────────────────────────────────────────────────────────────────
def generate_questions(topic_name, count=10, language="English"):
    """
    Tries every model in the waterfall until one succeeds.
    v1beta (Gemini 2.0) → v1 (Gemini 1.5) fallback chain.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment.")

    models = _build_model_list(api_key)

    prompt = f"""
Generate exactly {count} multiple-choice questions about "{topic_name}" in {language}.
Return ONLY a valid JSON array. Each element must have these exact keys:
"text", "option_a", "option_b", "option_c", "option_d", "correct_answer" (A/B/C/D), "explanation".
"""

    last_error = ""
    for client, model_id in models:
        try:
            print(f"Trying model: {model_id}")

            @retry(
                wait=wait_fixed(5),
                stop=stop_after_attempt(2),
                retry=retry_if_exception(
                    lambda e: _is_quota_error(e) and not _is_daily_quota_exhausted(e)
                ),
                reraise=True,
            )
            def _call():
                return client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )

            response = _call()
            data = json.loads(response.text)
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
    """Translates a question dict to target_language. Falls back to original on failure."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    models = _build_model_list(api_key)

    prompt = f"""
Translate the following question and options into {target_language}.
Return ONLY a valid JSON object with the exact same keys: 'text', 'option_a', 'option_b', 'option_c', 'option_d'.

Input JSON:
{json.dumps(question_data)}
"""

    for client, model_id in models:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return json.loads(response.text)
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

    models = _build_model_list(api_key)

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

    for client, model_id in models:
        try:
            print(f"Translate-doc trying: {model_id}")
            response = client.models.generate_content(model=model_id, contents=prompt)
            result_text = response.text
            gc.collect()
            return result_text, was_truncated
        except Exception as e:
            print(f"Model {model_id} failed (translate_doc): {str(e)[:120]}")
            continue

    return "Daily AI limit reached. Please try again tomorrow.", was_truncated
