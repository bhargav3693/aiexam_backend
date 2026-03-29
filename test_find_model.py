import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("API KEY NOT FOUND!")
    exit(1)

models_to_test = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

def test_models(api_version):
    print(f"\n--- Testing API Version: {api_version} ---")
    try:
        if api_version == "default":
            client = genai.Client(api_key=api_key)
        else:
            client = genai.Client(api_key=api_key, http_options={'api_version': api_version})
            
        for model in models_to_test:
            try:
                print(f"Testing {model}...")
                response = client.models.generate_content(
                    model=model,
                    contents="Say 'OK'",
                )
                print(f"SUCCESS with {model}: {response.text.strip()}")
                return model, api_version
            except Exception as e:
                msg = str(e)
                if '429' in msg:
                    print(f"  -> Failed (429 Quota Exhausted)")
                elif '404' in msg:
                    print(f"  -> Failed (404 Not Found)")
                else:
                    print(f"  -> Failed (Other error): {msg[:100]}")
    except Exception as e:
        print(f"Client init error: {e}")
    return None, None

success_model, success_ver = test_models("default")
if not success_model:
    success_model, success_ver = test_models("v1")
if not success_model:
    success_model, success_ver = test_models("v1alpha")

print("\n====================")
if success_model:
    print(f"FOUND WORKING COMBINATION: Model: {success_model}, API Version: {success_ver}")
else:
    print("ALL MODELS FAILED. The API key has zero quota or billing issues.")
