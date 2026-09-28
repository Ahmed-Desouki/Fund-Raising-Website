from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

# Templates live under main/ so they aren't shadowed by django.contrib.admin's
# registration/password_reset_* templates (admin comes first in INSTALLED_APPS).
password_reset_views = [
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='main/password_reset_form.html',
        email_template_name='main/password_reset_email.txt',
        html_email_template_name='main/emails/password_reset.html',
        subject_template_name='main/password_reset_subject.txt',
    ), name='password_reset'),
    path('password-reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='main/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='main/password_reset_confirm.html',
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='main/password_reset_complete.html',
    ), name='password_reset_complete'),
]

urlpatterns = [
    path('', views.auth_page, name='auth_page'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),

    path('api/register/', views.api_register, name='api_register'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/resend-activation/', views.api_resend_activation, name='api_resend_activation'),
] + password_reset_views