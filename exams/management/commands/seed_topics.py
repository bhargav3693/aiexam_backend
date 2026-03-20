from django.core.management.base import BaseCommand
from exams.models import Topic


TOPICS = [
    {"name": "Quantitative Aptitude", "icon": "🧮", "description": "Number systems, percentages, ratios, probability, and sets.", "difficulty": "medium", "question_count": 20},
    {"name": "Logical Reasoning", "icon": "🧩", "description": "Syllogisms, seating arrangements, blood relations, and puzzles.", "difficulty": "medium", "question_count": 20},
    {"name": "Arithmetic", "icon": "➕", "description": "Basic arithmetic operations, fractions, decimals, and basic algebra.", "difficulty": "easy", "question_count": 15},
    {"name": "General Awareness", "icon": "🌍", "description": "Current affairs, basic history, geography, and general knowledge.", "difficulty": "easy", "question_count": 25},
    {"name": "Mathematics", "icon": "📐", "description": "Algebra, calculus, statistics, and number theory.", "difficulty": "medium", "question_count": 20},
    {"name": "Python Programming", "icon": "🐍", "description": "Core Python, OOP, data structures, and standard library.", "difficulty": "medium", "question_count": 25},
]


class Command(BaseCommand):
    help = "Seed the database with initial topics for the exam system."

    def handle(self, *args, **kwargs):
        created = 0
        for topic_data in TOPICS:
            obj, was_created = Topic.objects.get_or_create(
                name=topic_data["name"],
                defaults=topic_data,
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created} new topics. Total topics: {Topic.objects.count()}")
        )
