import os
import json
import google.generativeai as genai

def generate_questions(topic_name, count=10):
    """
    Calls the Gemini API to generate multiple-choice questions for a specific topic.
    Dynamically fetches the very first available text-generation model.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment.")

    genai.configure(api_key=api_key)
    
    # 1. Use genai.list_models() to get all available models
    all_models = genai.list_models()
    
    # 2. Filter the models using a list comprehension
    valid_models = [m for m in all_models if "generateContent" in m.supported_generation_methods]
    
    if not valid_models:
        raise ValueError("No generative models are available for this API key.")
        
    # 3. Select the VERY FIRST model name from that filtered list
    model_name = valid_models[0].name
    print(f"Dynamically Selected Gemini Model: {model_name}")
    
    # 4. Initialize the model using that dynamically found name
    model = genai.GenerativeModel(model_name)

    prompt = f"""
    Generate exactly {count} multiple-choice questions about '{topic_name}'.
    The questions should be appropriate for a college-level exam.
    Return ONLY a valid JSON array of objects, with no markdown formatting blocks.
    Each object MUST have the following keys:
    - "text": The question text.
    - "option_a": First option.
    - "option_b": Second option.
    - "option_c": Third option.
    - "option_d": Fourth option.
    - "correct_option": The correct answer, exactly one of "A", "B", "C", or "D".
    
    Ensure the JSON is valid and can be parsed by Python's json.loads().
    """

    # 5. Add a simple try-except block around the generate_content call
    try:
        response = model.generate_content(prompt)
        
        # 6. Ensure the JSON parsing logic safely removes any markdown blocks
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        return data
        
    except Exception as e:
        print(f"Gemini API Error with model {model_name}: {str(e)}")
        # Raise it back to ExamSessionCreateView, which translates it to HTTP 400
        raise e

def translate_question_data(question_data, target_language):
    """
    Uses Gemini to translate a question object to a target language.
    Dynamically fetches the first available generation model to avoid 404/quota errors.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=api_key)
    
    # Use genai.list_models() to iterate through available models
    all_models = genai.list_models()
    
    # Programmatically find the first available model supporting generateContent
    valid_models = [m for m in all_models if "generateContent" in m.supported_generation_methods]
    
    if not valid_models:
        raise ValueError("No generative models are available for this API key.")
        
    # Select the VERY FIRST model name from that filtered list
    model_name = valid_models[0].name
    print(f"Dynamically Selected Gemini Model for Translation: {model_name}")
    
    # Initialize model
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    Translate the following question and options into {target_language}.
    Return ONLY a valid JSON object with the exact same keys: 'text', 'option_a', 'option_b', 'option_c', 'option_d'.
    Do not include markdown code formatting blocks.
    
    Input JSON:
    {json.dumps(question_data)}
    """
    
    try:
        # Call model.generate_content() to translate
        response = model.generate_content(prompt)
        
        # Safely parse JSON response by stripping markdown formatting
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        
        return json.loads(text.strip())
        
    except Exception as e:
        print(f"Translation failed with dynamically found model {model_name}: {e}")
        raise ValueError(f"Failed to translate question with {model_name}. API Error: {str(e)}")
