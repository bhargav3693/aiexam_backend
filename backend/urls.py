from django.contrib import admin
from django.urls import path, include
from accounts.views import SafeTokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/exams/", include("exams.urls")),
    path("api/auth/refresh/", SafeTokenRefreshView.as_view(), name="token_refresh"),
]
