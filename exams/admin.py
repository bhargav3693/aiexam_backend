from django.contrib import admin
from .models import Topic, ExamSession

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name", "icon", "difficulty", "question_count"]

@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "time_limit_minutes", "status", "started_at"]
