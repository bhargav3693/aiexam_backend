from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        print("Registration Attempt Data:", request.data)
        try:
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
            import traceback
            error_msg = f"ERROR DURING REGISTER: {str(e)}"
            print("--- REGISTRATION CRASH LOG ---")
            print(error_msg)
            traceback.print_exc()
            print("------------------------------")
            return Response({"error": error_msg, "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
