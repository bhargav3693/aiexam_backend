import os
import django
import sys

sys.path.append('c:\\Users\\HAI\\Downloads\\aiexam')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings') # Assuming 'backend.settings' or 'aiexam.settings'
try:
    django.setup()
except Exception as e:
    print(f"Django setup error: {e}")

from exams.ai_service import generate_questions

print("Testing generate_questions...")
try:
    questions = generate_questions("Python Basics", count=1)
    print(questions)
except Exception as e:
    print(f"Error: {e}")
