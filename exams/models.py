from django.db import models
from django.conf import settings


class Topic(models.Model):
    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, default="📚")  # emoji
    question_count = models.PositiveIntegerField(default=10)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="medium")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ExamSession(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_sessions",
    )
    topics = models.ManyToManyField(Topic, related_name="sessions")
    time_limit_minutes = models.PositiveIntegerField(default=30)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    score = models.FloatField(null=True, blank=True)
    
    # Advanced features
    violation_count = models.IntegerField(default=0)
    is_locked_out = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Session #{self.id} by {self.user.email}"


class Question(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1, choices=[('A','A'),('B','B'),('C','C'),('D','D')])
    explanation = models.TextField(blank=True, null=True)
    trick = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.text[:50]


class UserResponse(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, null=True, blank=True, choices=[('A','A'),('B','B'),('C','C'),('D','D')])
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.session.id} - {self.question.id} : {self.is_correct}"
