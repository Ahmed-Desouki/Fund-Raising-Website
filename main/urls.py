from django.urls import path
from . import views

urlpatterns = [
    path('', views.auth_page, name='auth_page'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),

    path('api/register/', views.api_register, name='api_register'),
    path('api/login/', views.api_login, name='api_login'),
]