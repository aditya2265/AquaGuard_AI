from django.urls import path
from . import views

app_name = 'predictions'

urlpatterns = [
    path('', views.PredictionListView.as_view(), name='list'),
    path('<int:pk>/', views.PredictionDetailView.as_view(), name='detail'),
    path('<int:pk>/explain/', views.AIExplanationView.as_view(), name='explain'),
    # API endpoints
    path('api/', views.PredictionAPIListView.as_view(), name='api_list'),
    path('api/<int:pk>/', views.PredictionAPIDetailView.as_view(), name='api_detail'),
]
