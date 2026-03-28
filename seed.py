import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from exams.models import Topic

topics = [
    {'id': 1, 'name': 'Quantitative Aptitude', 'icon': '📊', 'difficulty': 'medium', 'description': 'Math and numbers'},
    {'id': 2, 'name': 'General Intelligence & Reasoning', 'icon': '🧠', 'difficulty': 'medium', 'description': 'Logic and puzzles'},
    {'id': 3, 'name': 'General Awareness', 'icon': '🌍', 'difficulty': 'medium', 'description': 'World knowledge'}
]
for t in topics:
    Topic.objects.update_or_create(id=t['id'], defaults={'name': t['name'], 'icon': t['icon'], 'difficulty': t['difficulty'], 'description': t['description']})

print("Topics have been successfully seeded!")
