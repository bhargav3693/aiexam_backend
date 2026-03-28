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
    topic_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list
    )
    topic_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False, default=list
    )
    time_limit_minutes = serializers.IntegerField(required=False, default=30)

    class Meta:
        model = ExamSession
        fields = [
            "id", "topics", "topic_ids", "topic_names", "time_limit_minutes",
            "started_at", "completed_at", "status", "score",
            "violation_count", "is_locked_out"
        ]
        read_only_fields = ["id", "started_at", "completed_at", "status", "score", "violation_count", "is_locked_out"]

    def create(self, validated_data):
        topic_ids = validated_data.pop("topic_ids", [])
        topic_names = validated_data.pop("topic_names", [])
        
        session = ExamSession.objects.create(**validated_data)
        
        topics_to_add = []
        
        # 1. Resolve any valid IDs
        if topic_ids:
            try:
                valid_topics = Topic.objects.filter(id__in=topic_ids)
                topics_to_add.extend(list(valid_topics))
            except Exception:
                pass
                
        # 2. Auto-create topics from names if they don't exist
        for name in topic_names:
            if name:
                # get_or_create ensures the DB has it permanently now
                topic, created = Topic.objects.get_or_create(name=name)
                if topic not in topics_to_add:
                    topics_to_add.append(topic)
                    
        if topics_to_add:
            session.topics.set(topics_to_add)
                
        return session

