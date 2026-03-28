from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .serializers import RegisterSerializer, UserSerializer, AdminUserUpdateSerializer
from django.contrib.auth import get_user_model

User = get_user_model()
from exams.models import ExamSession
from django.db.models import Count


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "user": UserSerializer(user).data,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            from rest_framework.exceptions import ValidationError
            if isinstance(e, ValidationError):
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            import traceback
            error_msg = f"ERROR DURING REGISTER: {str(e)}"
            print("--- REGISTRATION CRASH LOG ---")
            print(traceback.format_exc())
            print("------------------------------")
            return Response({"error": error_msg, "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomLoginView(TokenObtainPairView):
    pass


class SafeTokenRefreshView(TokenRefreshView):
    """
    Wraps the standard JWT refresh view.
    If the user no longer exists in the DB (wiped SQLite on Render),
    returns a clean 401 instead of crashing with 500.
    """
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            error_str = str(e)
            print(f"SafeTokenRefreshView caught: {error_str}", flush=True)
            # Return 401 so the axios interceptor clears token and redirects to /login
            return Response(
                {"detail": "Session expired. Please log in again."},
                status=status.HTTP_401_UNAUTHORIZED
            )


class ProfileView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
        
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

class AdminUserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.all().order_by("-date_joined")
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RegisterSerializer
        return UserSerializer

from rest_framework.views import APIView
class FixAdminView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        admin, created = User.objects.get_or_create(email="admin@test.com", defaults={"full_name": "System Admin"})
        admin.set_password("admin_password")
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True  # explicitly restoring just in case it was deactivated
        admin.save()
        return Response({"status": "Admin created/updated successfully! You can now log in at /login with admin@test.com and admin_password."})

class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = AdminUserUpdateSerializer
    permission_classes = [IsAdminUser]

class AdminSystemActivityView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        new_users = list(User.objects.order_by('-date_joined')[:25])
        recent_exams = list(ExamSession.objects.select_related('user').order_by('-started_at')[:25])
        
        events = []
        for u in new_users:
            events.append({
                "type": "user_joined",
                "timestamp": u.date_joined,
                "message": f"New user joined: {u.full_name or u.email}"
            })
        for e in recent_exams:
            events.append({
                "type": "exam_started",
                "timestamp": e.started_at,
                "message": f"User {e.user.email} started a new exam session."
            })
            if e.completed_at:
                events.append({
                    "type": "exam_completed",
                    "timestamp": e.completed_at,
                    "message": f"User {e.user.email} completed their exam with score {e.score}."
                })
                
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        for ev in events:
            ev["timestamp"] = ev["timestamp"].isoformat()
            
        return Response(events[:50])

class AdminUserActivityView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        users = list(User.objects.annotate(
            exam_count=Count('exam_sessions')
        ).order_by('-date_joined')[:100])
        
        data = []
        for u in users:
            data.append({
                "id": u.id,
                "name": u.full_name or "No Name",
                "email": u.email,
                "date_joined": u.date_joined.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "exam_count": u.exam_count,
            })
        return Response(data)

class AdminSpecificUserActivityView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request, user_id):
        from django.shortcuts import get_object_or_404
        user = get_object_or_404(User, id=user_id)
        exams = ExamSession.objects.filter(user=user).order_by('-started_at')
        
        events = [{
            "type": "user_joined",
            "timestamp": user.date_joined.isoformat(),
            "message": f"User {user.email} joined the platform."
        }]
        for e in exams:
            events.append({
                "type": "exam_started",
                "timestamp": e.started_at.isoformat(),
                "message": f"Started exam session #{e.id}."
            })
            if e.completed_at:
                events.append({
                    "type": "exam_completed",
                    "timestamp": e.completed_at.isoformat(),
                    "message": f"Completed exam session #{e.id} with score {e.score}.",
                    "score": e.score,
                    "exam_id": e.id
                })
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        return Response(events)

