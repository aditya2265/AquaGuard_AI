from django.contrib import admin
from .models import WaterMeasurement, WeatherMeasurement


@admin.register(WaterMeasurement)
class WaterMeasurementAdmin(admin.ModelAdmin):
    list_display = ('region', 'date', 'reservoir_level', 'rainfall_mm', 'water_consumption_mld', 'is_demo_data')
    list_filter = ('region', 'is_demo_data')
    search_fields = ('region__name',)
    date_hierarchy = 'date'
    ordering = ('-date',)


@admin.register(WeatherMeasurement)
class WeatherMeasurementAdmin(admin.ModelAdmin):
    list_display = ('region', 'date', 'temperature_celsius', 'humidity_percent', 'wind_speed_kmh', 'is_demo_data')
    list_filter = ('region', 'is_demo_data')
    search_fields = ('region__name',)
    date_hierarchy = 'date'
    ordering = ('-date',)
