from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Topic, ExamSession, Question, UserResponse
from .serializers import TopicSerializer, ExamSessionSerializer, QuestionSerializer
from .ai_service import generate_questions, translate_question_data

class TopicListView(generics.ListAPIView):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    permission_classes = [AllowAny]


import traceback
from rest_framework.exceptions import ValidationError

class ExamSessionCreateView(generics.CreateAPIView):
    serializer_class = ExamSessionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Save session first
        session = serializer.save(user=self.request.user)
        
        # Determine topics for question generation
        topic_names = [t.name for t in session.topics.all()]
        combined_topic = " and ".join(topic_names) if topic_names else "General Knowledge"
        
        # Extract language from frontend request
        target_language = self.request.data.get("language", "English")
        
        try:
            # Generate 30 questions using Gemini with strict language
            q_data = generate_questions(combined_topic, count=30, language=target_language)
            
            # Save questions to DB linked to this session
            for q in q_data:
                Question.objects.create(
                    session=session,
                    text=q.get("text", "Missing Question Text"),
                    option_a=q.get("option_a", ""),
                    option_b=q.get("option_b", ""),
                    option_c=q.get("option_c", ""),
                    option_d=q.get("option_d", ""),
                    correct_option=q.get("correct_option", "A")
                )
        except Exception as e:
            # Robust error handling: print detailed logs and raise 400 validation error
            print("\n" + "="*50)
            print(f"CRITICAL ERROR: Failed to create exam session for user '{self.request.user.email}'.")
            print(f"Topic: {combined_topic}")
            print("Exception Details:")
            traceback.print_exc()
            print("="*50 + "\n")
            
            session.delete()
            raise ValidationError({"detail": f"Failed to generate AI questions: {str(e)}"})


class ExamSessionDetailView(generics.RetrieveAPIView):
    serializer_class = ExamSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExamSession.objects.filter(user=self.request.user)


class UserExamSessionListView(generics.ListAPIView):
    serializer_class = ExamSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExamSession.objects.filter(user=self.request.user)


class ExamQuestionsView(generics.ListAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs["session_id"]
        # Ensure user owns the session
        session = get_object_or_404(ExamSession, id=session_id, user=self.request.user)
        return Question.objects.filter(session=session)


class ExamSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(ExamSession, id=session_id, user=request.user)

        if session.status == "completed":
            return Response({"detail": "Exam already submitted."}, status=status.HTTP_400_BAD_REQUEST)

        answers = request.data.get("answers", {})  # expected format: {question_id: selected_option} e.g. {"15": "A"}
        violation_count = int(request.data.get("violation_count", 0))
        is_locked_out = bool(request.data.get("is_locked_out", False))
        
        # Grade answers
        questions = session.questions.all()
        correct_count = 0
        detailed_results = []
        
        for q in questions:
            selected = answers.get(str(q.id))
            is_correct = False
            
            if isinstance(selected, int) or (isinstance(selected, str) and selected.isdigit()):
                options_map = {0: "A", 1: "B", 2: "C", 3: "D"}
                selected_letter = options_map.get(int(selected))
            else:
                selected_letter = str(selected).upper() if selected else None

            if selected_letter == q.correct_option:
                correct_count += 1
                is_correct = True
            
            UserResponse.objects.create(
                session=session,
                question=q,
                selected_option=selected_letter,
                is_correct=is_correct
            )
            
            detailed_results.append({
                "id": q.id,
                "text": q.text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "user_answer": selected_letter if selected_letter else "Unattempted",
                "correct_answer": q.correct_option,
                "is_correct": is_correct
            })
            
        total_q = questions.count()
        score_percent = (correct_count / total_q * 100) if total_q > 0 else 0
        
        session.score = score_percent
        session.status = "completed"
        session.completed_at = timezone.now()
        session.violation_count = violation_count
        session.is_locked_out = is_locked_out
        session.save()
        
        return Response({
            "score": score_percent,
            "correct_count": correct_count,
            "total_questions": total_q,
            "attempted_count": len(answers),
            "violation_count": violation_count,
            "is_locked_out": is_locked_out,
            "detailed_results": detailed_results
        }, status=status.HTTP_200_OK)

from rest_framework.permissions import AllowAny, IsAuthenticated
import traceback

class TranslateQuestionView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        question_data = request.data.get('question')
        target_language = request.data.get('language')
        
        if not question_data or not target_language:
            return Response({"error": "question and language required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            translated = translate_question_data(question_data, target_language)
            return Response(translated)
        except Exception as e:
            print("Translate API Exception Triggered:")
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
