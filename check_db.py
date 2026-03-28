import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from exams.models import ExamSession, Question
session = ExamSession.objects.last()
if session:
    print(f"Latest Session ID: {session.id}, Started at: {session.started_at}")
    questions = session.questions.all()
    print(f"Number of questions: {questions.count()}")
    if questions.exists():
        first_q = questions.first()
        print(f"Q1 ID: {first_q.id}")
        print(f"Q1 Explanation: {first_q.explanation}")
        print(f"Q1 Trick: {first_q.trick}")
else:
    print("No sessions found.")
