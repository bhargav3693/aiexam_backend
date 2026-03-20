from rest_framework import serializers
from .models import Topic, ExamSession, Question, UserResponse


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ["id", "name", "description", "icon", "question_count", "difficulty"]


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "text", "option_a", "option_b", "option_c", "option_d"]
        # Notice correct_option is omitted so it's not leaked to the frontend

class ExamSessionSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, read_only=True)
    topic_ids = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(), many=True, write_only=True
    )

    class Meta:
        model = ExamSession
        fields = [
            "id", "topics", "topic_ids", "time_limit_minutes",
            "started_at", "completed_at", "status", "score",
            "violation_count", "is_locked_out"
        ]
        read_only_fields = ["id", "started_at", "completed_at", "status", "score", "violation_count", "is_locked_out"]

    def create(self, validated_data):
        topic_ids = validated_data.pop("topic_ids")
        session = ExamSession.objects.create(**validated_data)
        session.topics.set(topic_ids)
        return session

