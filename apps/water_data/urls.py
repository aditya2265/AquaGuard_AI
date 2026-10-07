from django.urls import path
from . import views

app_name = 'water_data'

urlpatterns = [
    path('import/', views.DataImportView.as_view(), name='import'),
    path('list/', views.WaterDataListView.as_view(), name='list'),
    # API endpoints
    path('api/water/', views.WaterMeasurementAPIListView.as_view(), name='api_water_list'),
    path('api/weather/', views.WeatherMeasurementAPIListView.as_view(), name='api_weather_list'),
]
