import os
import json
import gc
from google import genai
from google.genai import types
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception

def generate_questions(topic_name, count=10, language="English"):
    """
    Calls the Gemini API to generate multiple-choice questions for a specific topic.
    Dynamically fetches the very first available text-generation model.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment.")

    client = genai.Client(api_key=api_key)
    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]

    # Build the prompt BEFORE the loop so it is always in scope
    prompt = f"""
    Generate exactly {count} multiple-choice questions about "{topic_name}" in {language}.
    Each question must have 4 options (option_a, option_b, option_c, option_d) and a correct_answer field
    containing the letter of the correct option (e.g. "A", "B", "C", or "D").
    Return ONLY a valid JSON array of question objects with keys:
    "text", "option_a", "option_b", "option_c", "option_d", "correct_answer", "explanation".
    """

    @retry(
        wait=wait_fixed(10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception(lambda e: "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)),
        reraise=True
    )
    def call_gemini(model_id, prompt_text):
        return client.models.generate_content(
            model=model_id,
            contents=prompt_text,
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )

    last_error = ""
    for model_id in models_to_try:
        try:
            response = call_gemini(model_id, prompt)  # 'prompt' is now defined above
            data = json.loads(response.text)
            gc.collect()
            return data
        except Exception as e:
            last_error = str(e)
            print(f"Model {model_id} failed: {last_error}")
            continue

    # Final cleanup before return
    gc.collect()
    
    # Check for quota exhaustion specifically
    if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
        return {"error": "Daily AI limit reached. Please try again tomorrow."}
        
    raise Exception(f"AI Generation failed: {last_error}")

def translate_question_data(question_data, target_language):
    """
    Uses Gemini to translate a question object to a target language.
    Dynamically fetches the first available generation model to avoid 404/quota errors.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    models_to_try = [
        "gemini-2.5-flash", 
        "gemini-2.0-flash", 
        "gemini-flash-latest", 
        "gemini-pro-latest", 
        "gemini-2.5-pro"
    ]
    
    prompt = f"""
    Translate the following question and options into {target_language}.
    Return ONLY a valid JSON object with the exact same keys: 'text', 'option_a', 'option_b', 'option_c', 'option_d'.
    
    Input JSON:
    {json.dumps(question_data)}
    """
    
    for model_id in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                )
            )
            return json.loads(response.text)
            
        except Exception as e:
            error_str = str(e)
            print(f"Model {model_id} failed during translation: {error_str}. Trying next...")
            continue

    # If all models fail, just return the untranslated data
    print("All translation models failed. Falling back to original language.")
    return question_data

def translate_document(text, target_language):
    """
    Uses Gemini to translate a plain text document to a target language.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    models_to_try = [
        "gemini-2.5-flash", 
        "gemini-2.0-flash", 
        "gemini-flash-latest", 
        "gemini-pro-latest", 
        "gemini-2.5-pro"
    ]
    
    was_truncated = False
    if len(text) > 2000:
        text = text[:2000]
        was_truncated = True

    # Free up memory explicitly
    gc.collect()

    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
    
    @retry(
        wait=wait_fixed(10),
        stop=stop_after_attempt(2),
        retry=retry_if_exception(lambda e: "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)),
        reraise=True
    )
    def call_gemini_translate(model_id, prompt_text):
        return client.models.generate_content(model=model_id, contents=prompt_text)

    prompt = f"""
Translate the following text into {target_language}, but provide a bilingual line-by-line interleaving format...
{text}
"""
    del text
    gc.collect()
    
    for model_id in models_to_try:
        try:
            response = call_gemini_translate(model_id, prompt)
            result_text = response.text
            gc.collect()
            return result_text, was_truncated
        except Exception as e:
            print(f"Model {model_id} failed during document translation: {str(e)}")
            continue

    return "Daily AI limit reached. Please try again tomorrow.", was_truncated
