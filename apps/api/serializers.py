"""
Additional serializers for the consolidated API.
App-level serializers already exist in each app's serializers.py;
this module adds any extra cross-app or composite serializers.
"""
from rest_framework import serializers

from apps.regions.models import Region
from apps.water_data.models import WaterMeasurement, WeatherMeasurement
from apps.predictions.models import WaterPrediction, RiskAssessment
from apps.alerts.models import Alert
from apps.recommendations.models import Recommendation


class RiskSummarySerializer(serializers.ModelSerializer):
    """Compact per-region risk summary used by dashboard and risk endpoints."""
    latest_risk_level = serializers.SerializerMethodField()
    latest_risk_score = serializers.SerializerMethodField()
    latest_risk_color = serializers.SerializerMethodField()
    latest_prediction_date = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = (
            'id', 'name', 'state', 'country',
            'latest_risk_level', 'latest_risk_score',
            'latest_risk_color', 'latest_prediction_date',
        )

    def _latest_prediction(self, obj):
        cache = self.context.setdefault('_pred_cache', {})
        if obj.pk not in cache:
            cache[obj.pk] = obj.predictions.select_related('risk_assessment').first()
        return cache[obj.pk]

    def get_latest_risk_level(self, obj):
        pred = self._latest_prediction(obj)
        return pred.risk_level if pred else 'UNKNOWN'

    def get_latest_risk_score(self, obj):
        pred = self._latest_prediction(obj)
        if pred and hasattr(pred, 'risk_assessment'):
            return pred.risk_assessment.risk_score
        return None

    def get_latest_risk_color(self, obj):
        from ml.risk_engine import get_risk_color
        pred = self._latest_prediction(obj)
        level = pred.risk_level if pred else 'LOW'
        return get_risk_color(level)

    def get_latest_prediction_date(self, obj):
        pred = self._latest_prediction(obj)
        return pred.prediction_date if pred else None


class DashboardSummarySerializer(serializers.Serializer):
    total_regions = serializers.IntegerField()
    critical_regions = serializers.IntegerField()
    high_risk_regions = serializers.IntegerField()
    moderate_risk_regions = serializers.IntegerField()
    low_risk_regions = serializers.IntegerField()
    unread_alerts = serializers.IntegerField()
    total_predictions = serializers.IntegerField()
    regions = RiskSummarySerializer(many=True)
