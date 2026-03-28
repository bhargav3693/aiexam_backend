import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from exams.models import Topic
with open('topics_output.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps(list(Topic.objects.values('id', 'name', 'difficulty', 'icon'))))
