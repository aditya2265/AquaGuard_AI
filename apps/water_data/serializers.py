from rest_framework import serializers
from .models import WaterMeasurement, WeatherMeasurement


class WaterMeasurementSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = WaterMeasurement
        fields = '__all__'


class WeatherMeasurementSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = WeatherMeasurement
        fields = '__all__'
