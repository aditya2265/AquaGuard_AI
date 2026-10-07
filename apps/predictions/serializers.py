from rest_framework import serializers
from .models import WaterPrediction, RiskAssessment


class RiskAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskAssessment
        fields = '__all__'


class WaterPredictionSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)
    risk_assessment = RiskAssessmentSerializer(read_only=True)

    class Meta:
        model = WaterPrediction
        fields = '__all__'
