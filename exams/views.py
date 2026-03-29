import sys
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
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

class ExamSessionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # ================================================================
        # GOD MODE BYPASS — Zero serializer validation, raw ORM creation
        # ================================================================
        print("\n" + "="*60, flush=True)
        print("GOD MODE INCOMING:", dict(request.data), flush=True)
        print("USER:", request.user, "| IS_AUTH:", request.user.is_authenticated, flush=True)

        try:
            data          = request.data
            language      = data.get("language", "English")
            time_limit    = int(data.get("time_limit_minutes") or data.get("duration") or 30)
            topic_names_in = list(data.get("topic_names") or [])
            topic_ids_in   = list(data.get("topic_ids") or [])
            topics_in      = list(data.get("topics") or [])

            # Collect all topic names from every possible format
            names_to_create = []
            for name in topic_names_in:
                if isinstance(name, str) and name.strip():
                    names_to_create.append(name.strip())
            for item in topics_in:
                if isinstance(item, dict):
                    n = item.get("name") or item.get("title", "")
                    if n:
                        names_to_create.append(n.strip())
                elif isinstance(item, str) and item.strip():
                    names_to_create.append(item.strip())

            print("TOPICS TO RESOLVE:", names_to_create, flush=True)

            # get_or_create every topic by name
            resolved = []
            for name in names_to_create:
                topic, created = Topic.objects.get_or_create(name=name)
                if created:
                    print(f"  AUTO-CREATED: '{name}' id={topic.id}", flush=True)
                resolved.append(topic)

            # Also grab valid numeric IDs
            for tid in topic_ids_in:
                try:
                    t = Topic.objects.get(id=int(tid))
                    if t not in resolved:
                        resolved.append(t)
                except (Topic.DoesNotExist, ValueError, TypeError):
                    pass

            # Guarantee at least one topic
            if not resolved:
                t, _ = Topic.objects.get_or_create(name="General Knowledge")
                resolved.append(t)

            print("RESOLVED:", [t.name for t in resolved], flush=True)

            # Create session directly
            session = ExamSession.objects.create(user=request.user, time_limit_minutes=time_limit)
            session.topics.set(resolved)
            session.save()
            print(f"SESSION id={session.id} CREATED", flush=True)

            # Generate AI questions
            combined_topic = " and ".join([t.name for t in resolved])
            print(f"GENERATING for '{combined_topic}' in '{language}'", flush=True)

            q_data = generate_questions(combined_topic, count=15, language=language)
            for q in q_data:
                Question.objects.create(
                    session=session,
                    text=q.get("text", "Question unavailable"),
                    option_a=q.get("option_a", ""),
                    option_b=q.get("option_b", ""),
                    option_c=q.get("option_c", ""),
                    option_d=q.get("option_d", ""),
                    correct_option=q.get("correct_option", "A"),
                    explanation=q.get("explanation", ""),
                    trick=q.get("trick", ""),
                )

            print(f"SUCCESS: {len(q_data)} questions created for session {session.id}", flush=True)
            return Response({"id": session.id, "message": "Exam started!"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            traceback.print_exc()
            error_msg = str(e)
            print("GOD MODE ERROR:", error_msg, flush=True)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                return Response(
                    {"detail": "Server is busy or API quota reached. Please wait 1 minute and try again."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            # Return 200 (not 400!) so frontend can always read the error
            return Response({"error": error_msg, "id": None}, status=status.HTTP_200_OK)


# ============================================================
# NUCLEAR BACKDOOR VIEW — Completely bypasses DRF ViewSets
# ============================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def force_start_exam(request):
    try:
        print("\n" + "="*60, flush=True)
        print("--- NUCLEAR PAYLOAD ---", dict(request.data), flush=True)
        print("USER:", request.user, "| AUTH:", request.user.is_authenticated, flush=True)

        language      = request.data.get('language', 'English')
        time_limit    = int(request.data.get('time_limit_minutes') or request.data.get('duration') or 30)
        topic_names_in = list(request.data.get('topic_names') or [])
        topic_ids_in   = list(request.data.get('topic_ids') or [])
        topics_raw     = list(request.data.get('topics') or [])

        # Collect names from all possible formats
        names = []
        for n in topic_names_in:
            if isinstance(n, str) and n.strip():
                names.append(n.strip())
        for item in topics_raw:
            if isinstance(item, dict):
                n = item.get('name') or item.get('title', '')
                if n: names.append(n.strip())
            elif isinstance(item, str) and item.strip():
                names.append(item.strip())

        print("TOPIC NAMES:", names, flush=True)

        # get_or_create topics
        resolved = []
        for name in names:
            topic, created = Topic.objects.get_or_create(name=name)
            if created:
                print(f"  CREATED topic '{name}' id={topic.id}", flush=True)
            resolved.append(topic)

        # Also grab any valid IDs
        for tid in topic_ids_in:
            try:
                t = Topic.objects.get(id=int(tid))
                if t not in resolved:
                    resolved.append(t)
            except (Topic.DoesNotExist, ValueError, TypeError):
                pass

        # Always ensure at least one topic
        if not resolved:
            t, _ = Topic.objects.get_or_create(name='General Knowledge')
            resolved.append(t)

        print("RESOLVED TOPICS:", [t.name for t in resolved], flush=True)

        # Create session directly via ORM
        session = ExamSession.objects.create(user=request.user, time_limit_minutes=time_limit)
        session.topics.set(resolved)
        session.save()
        print(f"SESSION id={session.id} CREATED", flush=True)

        # Generate AI questions
        combined = ' and '.join([t.name for t in resolved])
        print(f"GENERATING: '{combined}' in '{language}'", flush=True)

        q_data = generate_questions(combined, count=15, language=language)
        for q in q_data:
            Question.objects.create(
                session=session,
                text=q.get('text', 'Question unavailable'),
                option_a=q.get('option_a', ''),
                option_b=q.get('option_b', ''),
                option_c=q.get('option_c', ''),
                option_d=q.get('option_d', ''),
                correct_option=q.get('correct_option', 'A'),
                explanation=q.get('explanation', ''),
                trick=q.get('trick', ''),
            )

        print(f"SUCCESS: {len(q_data)} questions for session {session.id}", flush=True)
        return Response({'id': session.id, 'message': 'Exam forced started!'}, status=201)

    except Exception as e:
        import traceback as tb
        tb.print_exc()
        error_msg = str(e)
        print('NUCLEAR ERROR:', error_msg, flush=True)
        if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg:
            return Response(
                {'detail': 'Server is busy or API quota reached. Please wait 1 minute and try again.'},
                status=429,
            )
        return Response({'error': error_msg, 'id': None}, status=200)  # 200 so frontend can always read it


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

class SessionResultDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(ExamSession, id=session_id, user=request.user)

        questions = session.questions.all()
        responses = {r.question_id: r for r in session.responses.all()}
        
        detailed_results = []
        for q in questions:
            user_response = responses.get(q.id)
            selected_letter = user_response.selected_option if user_response and user_response.selected_option else "Unattempted"
            is_correct = user_response.is_correct if user_response else False
            
            detailed_results.append({
                "id": q.id,
                "text": q.text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_option": q.correct_option,
                "explanation": q.explanation,
                "trick": q.trick,
                "user_answer": selected_letter,
                "is_correct": is_correct
            })
            
        return Response({
            "id": session.id,
            "status": session.status,
            "score": session.score,
            "time_limit_minutes": session.time_limit_minutes,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "violation_count": session.violation_count,
            "is_locked_out": session.is_locked_out,
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

import PyPDF2
from rest_framework.parsers import MultiPartParser, FormParser
from .ai_service import translate_document

class TranslateDocumentView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        target_language = request.data.get('language')
        
        if not file_obj or not target_language:
            return Response({"error": "file and language required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Extract text from PDF
            pdf_reader = PyPDF2.PdfReader(file_obj)
            extracted_text = ""
            for page in pdf_reader.pages:
                extracted_text += page.extract_text() + "\n"
            
            # Translate text
            translated_text, was_truncated = translate_document(extracted_text, target_language)
            
            warning = ""
            if was_truncated:
                warning = "Note: Due to server limits, only the first part of the document was translated."

            # Keep one folder like translated_files to store
            import os
            import uuid
            from django.conf import settings
            
            translated_folder = os.path.join(settings.BASE_DIR, "translated_files")
            os.makedirs(translated_folder, exist_ok=True)
            
            safe_original_name = file_obj.name.replace(" ", "_")
            filename = f"translated_{target_language}_{safe_original_name}.txt"
            filepath = os.path.join(translated_folder, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(translated_text)

            return Response({"translated_text": translated_text, "filename": filename, "warning": warning})
        except Exception as e:
            print("Translate PDF Exception:")
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
