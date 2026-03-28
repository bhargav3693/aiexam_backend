from django.urls import path
from .views import (
    RegisterView, CustomLoginView, ProfileView, 
    AdminUserListCreateView, AdminUserDetailView, FixAdminView,
    AdminSystemActivityView, AdminUserActivityView, AdminSpecificUserActivityView
)

urlpatterns = [
    path('fix-admin/', FixAdminView.as_view(), name='fix-admin'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('admin/users/', AdminUserListCreateView.as_view(), name='admin-users-list'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-users-detail'),
    path('admin/system-activity/', AdminSystemActivityView.as_view(), name='admin-system-activity'),
    path('admin/user-activity/', AdminUserActivityView.as_view(), name='admin-user-activity'),
    path('admin/user-activity/<int:user_id>/', AdminSpecificUserActivityView.as_view(), name='admin-user-specific-activity'),
]
