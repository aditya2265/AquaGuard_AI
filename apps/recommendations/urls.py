from django.urls import path
from . import views

app_name = 'recommendations'

urlpatterns = [
    path('', views.RecommendationListView.as_view(), name='list'),
    path('<int:pk>/', views.RecommendationDetailView.as_view(), name='detail'),
    # API
    path('api/', views.RecommendationAPIListView.as_view(), name='api_list'),
]
