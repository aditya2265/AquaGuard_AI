from django.urls import path
from . import views

app_name = 'regions'

urlpatterns = [
    path('', views.RegionListView.as_view(), name='list'),
    path('map/', views.MapView.as_view(), name='map'),
    path('compare/', views.RegionComparisonView.as_view(), name='compare'),
    path('<int:pk>/', views.RegionDetailView.as_view(), name='detail'),
    # API endpoints
    path('api/', views.RegionAPIListView.as_view(), name='api_list'),
    path('api/<int:pk>/', views.RegionAPIDetailView.as_view(), name='api_detail'),
]
