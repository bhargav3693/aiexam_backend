import os
import json
import gc
from google import genai
from google.genai import types
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception

# ── Verified model names for the google-genai v1beta API ──────────────────────
# gemini-2.0-flash-lite  → lightest, own quota bucket, good first fallback
# gemini-2.0-flash       → standard free-tier model
# gemini-1.5-flash-8b    → smallest 1.5 series, separate quota
# gemini-1.5-flash-001   → pinned stable version (avoids latest-alias 404s)
# gemini-1.5-pro-001     → last resort, higher quality but slower
GENERATION_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash-001",
    "gemini-1.5-pro-001",
]

def _is_quota_error(e: Exception) -> bool:
    s = str(e)
    return "429" in s or "RESOURCE_EXHAUSTED" in s

def _is_daily_quota_exhausted(e: Exception) -> bool:
    """Daily quota cannot be fixed by retrying — skip to next model immediately."""
    s = str(e)
    return "GenerateRequestsPerDayPerProjectPerModel" in s or "limit: 0" in s


# ──────────────────────────────────────────────────────────────────────────────
def generate_questions(topic_name, count=10, language="English"):
    """
    Calls the Gemini API to generate multiple-choice questions.
    Tries several models in order; skips daily-quota-exhausted models immediately.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment.")

    client = genai.Client(api_key=api_key)

    # Prompt must be defined BEFORE the retry helper and the loop.
    prompt = f"""
Generate exactly {count} multiple-choice questions about "{topic_name}" in {language}.
Each question must have 4 options and a correct_answer field.
Return ONLY a valid JSON array. Each object must have these keys:
"text", "option_a", "option_b", "option_c", "option_d", "correct_answer" (one of A/B/C/D), "explanation".
"""

    @retry(
        wait=wait_fixed(8),
        stop=stop_after_attempt(2),
        # Only retry transient rate-limit errors, not daily quota exhaustion
        retry=retry_if_exception(
            lambda e: _is_quota_error(e) and not _is_daily_quota_exhausted(e)
        ),
        reraise=True,
    )
    def call_gemini(model_id, prompt_text):
        return client.models.generate_content(
            model=model_id,
            contents=prompt_text,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )

    last_error = ""
    for model_id in GENERATION_MODELS:
        try:
            print(f"Trying model: {model_id}")
            response = call_gemini(model_id, prompt)
            data = json.loads(response.text)
            gc.collect()
            print(f"Success with model: {model_id}")
            return data
        except Exception as e:
            last_error = str(e)
            print(f"Model {model_id} failed: {last_error[:120]}")
            continue

    gc.collect()

    if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
        return {"error": "Daily AI limit reached. Please try again tomorrow."}

    raise Exception(f"AI Generation failed: {last_error}")


# ──────────────────────────────────────────────────────────────────────────────
def translate_question_data(question_data, target_language):
    """
    Uses Gemini to translate a question object to a target language.
    Falls back to original data if all models fail.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
Translate the following question and options into {target_language}.
Return ONLY a valid JSON object with the exact same keys: 'text', 'option_a', 'option_b', 'option_c', 'option_d'.

Input JSON:
{json.dumps(question_data)}
"""

    for model_id in GENERATION_MODELS:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Model {model_id} failed during translation: {str(e)[:120]}. Trying next...")
            continue

    print("All translation models failed. Falling back to original language.")
    return question_data


# ──────────────────────────────────────────────────────────────────────────────
def translate_document(text, target_language):
    """
    Uses Gemini to translate a plain text document to a target language.
    Returns (translated_text, was_truncated).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)

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

    @retry(
        wait=wait_fixed(8),
        stop=stop_after_attempt(2),
        retry=retry_if_exception(
            lambda e: _is_quota_error(e) and not _is_daily_quota_exhausted(e)
        ),
        reraise=True,
    )
    def call_gemini_translate(model_id, prompt_text):
        return client.models.generate_content(model=model_id, contents=prompt_text)

    for model_id in GENERATION_MODELS:
        try:
            response = call_gemini_translate(model_id, prompt)
            result_text = response.text
            gc.collect()
            return result_text, was_truncated
        except Exception as e:
            print(f"Model {model_id} failed during document translation: {str(e)[:120]}")
            continue

    return "Daily AI limit reached. Please try again tomorrow.", was_truncated
