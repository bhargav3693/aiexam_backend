import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from accounts.views import CustomTokenObtainPairSerializer

print("Testing with 'email' key:")
try:
    serializer = CustomTokenObtainPairSerializer(data={"email": "admin@aiexam.com", "password": "AdminPassword123!"})
    serializer.is_valid(raise_exception=True)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")

from django.contrib.auth import authenticate
user = authenticate(email="admin@aiexam.com", password="AdminPassword123!")
if user:
    print(f"Authenticate function returns: {user.email}, is_active: {user.is_active}")
else:
    print("Authenticate function returns None")
