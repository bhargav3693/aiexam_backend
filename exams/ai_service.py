import os
import re
import json
import gc
from dotenv import load_dotenv
from google import genai

# Load environment variables (crucial for local testing)
load_dotenv()

# ── Model Configuration ─────────────────────────────────────────────────────────
# Overridden to gemini-2.5-flash because previous models triggered Quota 429s
MODEL_ID = "gemini-2.5-flash"
USE_MOCK_DATA = False

def _make_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
         raise ValueError("GEMINI_API_KEY is not set in environment.")
    return genai.Client(api_key=api_key)

def _extract_json(text: str):
    """
    Robustly pull a JSON value out of a model response.
    Handles markdown code fences (```json ... ```) and bare JSON.
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())

def _call_model(client, prompt):
    return client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
    )

# ──────────────────────────────────────────────────────────────────────────────
def generate_questions(topic_name, count=15, language="English"):
    if USE_MOCK_DATA:
        print(f"DEBUG: BYPASSING AI - Returning MOCK data for '{topic_name}'", flush=True)
        return []

    # Highly optimized prompt to use fewer tokens
    prompt = f"""
Generate exactly {count} multiple-choice questions about "{topic_name}" in {language}.
Return ONLY a valid JSON array of objects. Keys must be exactly:
"text", "option_a", "option_b", "option_c", "option_d", "correct_option", "explanation", "trick".
Be concise.
"""
    client = _make_client()
    try:
        response = _call_model(client, prompt)
        data = _extract_json(response.text)
        gc.collect()
        return data
    except Exception as e:
         raise Exception(f"AI Generation failed: {str(e)}")

# ──────────────────────────────────────────────────────────────────────────────
def translate_question_data(question_data, target_language):
    prompt = f"""
Translate to {target_language}. Return ONLY valid JSON with the same exact keys.
{json.dumps(question_data)}
"""
    client = _make_client()
    try:
        response = _call_model(client, prompt)
        return _extract_json(response.text)
    except Exception as e:
        print(f"Translation failed: {str(e)[:120]}")
        return question_data

# ──────────────────────────────────────────────────────────────────────────────
def translate_document(text, target_language):
    was_truncated = False
    if len(text) > 2000:
        text = text[:2000]
        was_truncated = True

    prompt = f"""
Translate to {target_language}. Provide interleaved format (original, then translated).
{text}
"""
    client = _make_client()
    try:
        response = _call_model(client, prompt)
        gc.collect()
        return response.text, was_truncated
    except Exception as e:
        return f"Translation failed: {str(e)}", was_truncated
