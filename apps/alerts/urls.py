from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.AlertListView.as_view(), name='list'),
    path('mark-read/', views.AlertMarkReadView.as_view(), name='mark_all_read'),
    path('<int:pk>/mark-read/', views.AlertMarkReadView.as_view(), name='mark_read'),
    # API
    path('api/', views.AlertAPIListView.as_view(), name='api_list'),
]
