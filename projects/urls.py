from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('new/', views.project_create, name='project_create'),
    path('mine/', views.my_projects, name='my_projects'),
    path('donations/', views.my_donations, name='my_donations'),
    path('category/<int:pk>/', views.category_projects, name='category_projects'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/donate/', views.donate, name='donate'),
    path('<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('<int:pk>/rate/', views.rate_project, name='rate_project'),
    path('<int:pk>/report/', views.report_project, name='report_project'),
    path('<int:pk>/cancel/', views.cancel_project, name='cancel_project'),
    path('comments/<int:pk>/report/', views.report_comment, name='report_comment'),
]
