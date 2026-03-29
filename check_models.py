import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
    print("Default Client Models:")
    # Wait, the new genai SDK might use client.models.list()
    models = client.models.list()
    for m in models:
        if 'flash' in m.name:
            print(f"  - {m.name}")
except Exception as e:
    print(f"Error listing default models: {e}")

try:
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
    print("v1 Client Models:")
    models = client.models.list()
    for m in models:
        if 'flash' in m.name:
            print(f"  - {m.name}")
except Exception as e:
    print(f"Error listing v1 models: {e}")
