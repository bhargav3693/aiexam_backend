from django.urls import path
from .views import (
    TopicListView,
    ExamSessionCreateView,
    ExamSessionDetailView,
    UserExamSessionListView,
    ExamQuestionsView,
    ExamSubmitView,
    TranslateQuestionView,
)

urlpatterns = [
    path("topics/", TopicListView.as_view(), name="topic-list"),
    path("sessions/", ExamSessionCreateView.as_view(), name="session-create"),
    path("sessions/history/", UserExamSessionListView.as_view(), name="session-history"),
    path("sessions/<int:pk>/", ExamSessionDetailView.as_view(), name="session-detail"),
    path("sessions/<int:session_id>/questions/", ExamQuestionsView.as_view(), name="session-questions"),
    path("sessions/<int:session_id>/submit/", ExamSubmitView.as_view(), name="session-submit"),
    path("translate/", TranslateQuestionView.as_view(), name="translate-question"),
]
