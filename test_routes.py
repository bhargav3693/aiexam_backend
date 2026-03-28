import os
import django
import sys

sys.path.append('c:\\Users\\HAI\\Downloads\\aiexam')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings') 
django.setup()

from django.test import RequestFactory
from accounts.views import AdminSpecificUserActivityView, AdminSystemActivityView
from django.contrib.auth import get_user_model
User = get_user_model()

factory = RequestFactory()
request = factory.get('/')
admin_user = User.objects.filter(is_superuser=True).first()
request.user = admin_user

print("Initializing view instances directly to bypass middleware/permissions...")
view_specific = AdminSpecificUserActivityView()
view_specific.request = request

try:
    print("Testing specific user log logic:")
    res = view_specific.get(request, user_id=admin_user.id)
    print(f"Status Code: {res.status_code}")
    print(f"Data: {res.data}")
except Exception as e:
    import traceback
    traceback.print_exc()

view_system = AdminSystemActivityView()
view_system.request = request
try:
    print("Testing system log logic:")
    res2 = view_system.get(request)
    print(f"Status Code: {res2.status_code}")
except Exception as e:
    import traceback
    traceback.print_exc()
