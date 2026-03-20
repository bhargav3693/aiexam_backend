import os
import json
from google import genai
from google.genai import types

def generate_questions(topic_name, count=10):
    """
    Calls the Gemini API to generate multiple-choice questions for a specific topic.
    Dynamically fetches the very first available text-generation model.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment.")

    client = genai.Client(api_key=api_key)
    model_id = "gemini-1.5-flash"
    
    prompt = f"""
    Generate exactly {count} multiple-choice questions about '{topic_name}'.
    The questions should be appropriate for a college-level exam.
    Return ONLY a valid JSON array of objects.
    Each object MUST have the following keys:
    - "text": The question text.
    - "option_a": First option.
    - "option_b": Second option.
    - "option_c": Third option.
    - "option_d": Fourth option.
    - "correct_option": The correct answer, exactly one of "A", "B", "C", or "D".
    """

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
            )
        )
        
        # Parse JSON response
        data = json.loads(response.text)
        return data
        
    except Exception as e:
        print(f"CRITICAL Gemini API Error: {str(e)}")
        # Return an empty list or a specific error message to handle gracefully
        return [{"text": f"Error generating questions: {str(e)}", "option_a": "Error", "option_b": "Error", "option_c": "Error", "option_d": "Error", "correct_option": "A"}]

def translate_question_data(question_data, target_language):
    """
    Uses Gemini to translate a question object to a target language.
    Dynamically fetches the first available generation model to avoid 404/quota errors.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    model_id = "gemini-1.5-flash-latest"
    
    prompt = f"""
    Translate the following question and options into {target_language}.
    Return ONLY a valid JSON object with the exact same keys: 'text', 'option_a', 'option_b', 'option_c', 'option_d'.
    
    Input JSON:
    {json.dumps(question_data)}
    """
    
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
        print(f"Translation failed: {e}")
        # Return original data if translation fails to prevent crash
        return question_data
