import os
import json
import gc
from google import genai
from google.genai import types

def generate_questions(topic_name, count=10, language="English"):
    """
    Calls the Gemini API to generate multiple-choice questions for a specific topic.
    Dynamically fetches the very first available text-generation model.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment.")

    client = genai.Client(api_key=api_key)
    models_to_try = [
        "gemini-2.5-flash", 
        "gemini-2.0-flash", 
        "gemini-flash-latest", 
        "gemini-pro-latest", 
        "gemini-2.5-pro"
    ]
    
    prompt = f"""
    Generate exactly {count} MCQs about '{topic_name}' in {language}.
    Return ONLY a minified JSON array of objects. NO conversational text.
    Keys: "text", "option_a", "option_b", "option_c", "option_d", "correct_option", "explanation", "trick".
    """

    last_error = ""
    for model_id in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                )
            )
            data = json.loads(response.text)
            gc.collect()
            return data
            
        except Exception as e:
            error_str = str(e)
            last_error = error_str
            print(f"Model {model_id} failed: {error_str}. Trying next model...")
            continue

    # Final cleanup before return
    gc.collect()
    # If all models fail
    raise Exception(f"All AI models failed. Last error: {last_error}")

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
    if len(text) > 3000:
        text = text[:3000]
        was_truncated = True

    # Critical: Clear the original large string from memory immediately
    # (In Python, slicing creates a new string; we want to ensure the old one can be collected)
    # However, Python handles this behind the scenes. We'll proceed with the truncated string.

    prompt = f"""
Translate the following text into {target_language}, but provide a bilingual line-by-line interleaving format.
For every sentence or line in the original text, first output the original line, and immediately below it, output the translated {target_language} line.
Preserve the overall document structure and formatting as much as possible.

IMPORTANT: At the very end of your response (after all the translations), you MUST provide a brief summary of how accurately you were able to translate the text. Use exactly this format:

==============
Translation Metrics:
- Estimated Accuracy: [0-100%]
- Confidence Level: [Low/Medium/High/Very High] 
- Reasoning: [1-2 sentences explaining if there were any idioms, highly technical terms, or missing context that affected translation]

Text:
{text}
"""
    # Free up memory explicitly
    del text
    gc.collect()
    
    for model_id in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            result_text = response.text
            gc.collect()
            return result_text, was_truncated
            
        except Exception as e:
            error_str = str(e)
            print(f"Model {model_id} failed during document translation: {error_str}. Trying next...")
            continue

    return f"Translation failed. Could not translate text to {target_language}.", was_truncated
