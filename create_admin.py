import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

email = 'admin@aiexam.com'
password = 'AdminPassword123!'

# Force create or update the superuser
u, created = User.objects.get_or_create(email=email)
u.username = email
u.set_password(password)
u.is_superuser = True
u.is_staff = True
u.save()

if created:
    print(f"SUCCESS: Created new admin user: {email}")
else:
    print(f"SUCCESS: Updated existing admin user: {email}")
