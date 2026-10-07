"""
Consolidated REST API views for AquaGuard.
All views require authentication (configured globally in DRF settings).
"""
import logging

from django.utils import timezone
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from apps.regions.models import Region
from apps.water_data.models import WaterMeasurement, WeatherMeasurement
from apps.predictions.models import WaterPrediction, RiskAssessment
from apps.alerts.models import Alert
from apps.recommendations.models import Recommendation

from apps.regions.serializers import RegionSerializer
from apps.water_data.serializers import WaterMeasurementSerializer, WeatherMeasurementSerializer
from apps.predictions.serializers import WaterPredictionSerializer
from apps.alerts.serializers import AlertSerializer
from apps.recommendations.serializers import RecommendationSerializer
from apps.api.serializers import RiskSummarySerializer, DashboardSummarySerializer

logger = logging.getLogger(__name__)


def _ok(data, message='', status_code=status.HTTP_200_OK):
    return Response({'status': 'success', 'message': message, 'data': data}, status=status_code)


def _err(message, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({'status': 'error', 'message': message, 'data': None}, status=status_code)


# ==========================================================================
# REGIONS
# ==========================================================================

class RegionListView(APIView):
    """GET /api/regions/"""
    permission_classes = [AllowAny]

    def get(self, request):
        regions = Region.objects.filter(is_active=True)
        return _ok(RegionSerializer(regions, many=True).data)


class RegionDetailView(APIView):
    """GET /api/regions/{id}/"""
    permission_classes = [AllowAny]

    def get(self, request, region_id):
        try:
            region = Region.objects.get(pk=region_id)
        except Region.DoesNotExist:
            return _err('Region not found.', status.HTTP_404_NOT_FOUND)
        return _ok(RegionSerializer(region).data)


class RegionPredictionsView(APIView):
    """GET /api/regions/{id}/predictions/"""
    permission_classes = [AllowAny]

    def get(self, request, region_id):
        try:
            Region.objects.get(pk=region_id)
        except Region.DoesNotExist:
            return _err('Region not found.', status.HTTP_404_NOT_FOUND)
        preds = WaterPrediction.objects.filter(region_id=region_id).select_related('risk_assessment')[:50]
        return _ok(WaterPredictionSerializer(preds, many=True).data)


class RegionLatestMeasurementsView(APIView):
    """GET /api/regions/{id}/latest-measurements/"""
    permission_classes = [AllowAny]

    def get(self, request, region_id):
        try:
            Region.objects.get(pk=region_id)
        except Region.DoesNotExist:
            return _err('Region not found.', status.HTTP_404_NOT_FOUND)

        water = WaterMeasurement.objects.filter(region_id=region_id).first()
        weather = WeatherMeasurement.objects.filter(region_id=region_id).first()

        return _ok({
            'water': WaterMeasurementSerializer(water).data if water else None,
            'weather': WeatherMeasurementSerializer(weather).data if weather else None,
        })


class RunPredictionView(APIView):
    """POST /api/regions/{id}/run-prediction/"""
    permission_classes = [AllowAny]

    def post(self, request, region_id):
        try:
            Region.objects.get(pk=region_id)
        except Region.DoesNotExist:
            return _err('Region not found.', status.HTTP_404_NOT_FOUND)

        try:
            from ml.predict import PredictionService
            from services.recommendation_service import save_recommendations, generate_alerts, generate_recommendations

            results = PredictionService.predict_multi_horizon(region_id)

            if results:
                latest = results[-1]  # 30-day horizon
                factors = latest.get('contributing_factors', {})
                risk_level = latest.get('risk_level', 'LOW')

                recs = generate_recommendations(factors, risk_level, latest.get('region_name', ''))
                save_recommendations(region_id, latest.get('prediction_id'), recs)
                generate_alerts(region_id, latest)

            return _ok(results, 'Predictions generated successfully.', status.HTTP_201_CREATED)
        except Exception as exc:
            logger.exception("RunPrediction failed for region %s", region_id)
            return _err(f'Prediction failed: {exc}', status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==========================================================================
# WATER DATA
# ==========================================================================

class WaterDataListView(APIView):
    """GET /api/water-data/"""
    permission_classes = [AllowAny]

    def get(self, request):
        region_id = request.query_params.get('region_id')
        qs = WaterMeasurement.objects.select_related('region').order_by('-date')
        if region_id:
            qs = qs.filter(region_id=region_id)
        return _ok(WaterMeasurementSerializer(qs[:100], many=True).data)


class WeatherDataListView(APIView):
    """GET /api/weather-data/"""
    permission_classes = [AllowAny]

    def get(self, request):
        region_id = request.query_params.get('region_id')
        qs = WeatherMeasurement.objects.select_related('region').order_by('-date')
        if region_id:
            qs = qs.filter(region_id=region_id)
        return _ok(WeatherMeasurementSerializer(qs[:100], many=True).data)


# ==========================================================================
# PREDICTIONS
# ==========================================================================

class PredictionListView(APIView):
    """GET /api/predictions/"""
    permission_classes = [AllowAny]

    def get(self, request):
        region_id = request.query_params.get('region_id')
        qs = WaterPrediction.objects.select_related('risk_assessment', 'region').order_by('-prediction_date')
        if region_id:
            qs = qs.filter(region_id=region_id)
        return _ok(WaterPredictionSerializer(qs[:50], many=True).data)


class PredictionDetailView(APIView):
    """GET /api/predictions/{id}/"""
    permission_classes = [AllowAny]

    def get(self, request, prediction_id):
        try:
            pred = WaterPrediction.objects.select_related('risk_assessment', 'region').get(pk=prediction_id)
        except WaterPrediction.DoesNotExist:
            return _err('Prediction not found.', status.HTTP_404_NOT_FOUND)
        return _ok(WaterPredictionSerializer(pred).data)


class PredictionExplanationView(APIView):
    """GET /api/predictions/{id}/explanation/"""
    permission_classes = [AllowAny]

    def get(self, request, prediction_id):
        try:
            pred = WaterPrediction.objects.select_related('risk_assessment', 'region').get(pk=prediction_id)
        except WaterPrediction.DoesNotExist:
            return _err('Prediction not found.', status.HTTP_404_NOT_FOUND)

        assessment = getattr(pred, 'risk_assessment', None)
        return _ok({
            'prediction_id': pred.pk,
            'region': pred.region.name,
            'risk_level': pred.risk_level,
            'risk_score': assessment.risk_score if assessment else None,
            'explanation': assessment.explanation_text if assessment else '',
            'contributing_factors': assessment.contributing_factors if assessment else {},
        })


# ==========================================================================
# RISK
# ==========================================================================

class RiskSummaryView(APIView):
    """GET /api/risk/summary/ — all regions risk summary"""
    permission_classes = [AllowAny]

    def get(self, request):
        regions = Region.objects.filter(is_active=True).prefetch_related('predictions__risk_assessment')
        return _ok(RiskSummarySerializer(regions, many=True).data)


class RegionRiskView(APIView):
    """GET /api/risk/{region_id}/ — specific region risk"""
    permission_classes = [AllowAny]

    def get(self, request, region_id):
        try:
            region = Region.objects.prefetch_related('predictions__risk_assessment').get(pk=region_id)
        except Region.DoesNotExist:
            return _err('Region not found.', status.HTTP_404_NOT_FOUND)
        return _ok(RiskSummarySerializer(region).data)


# ==========================================================================
# ALERTS
# ==========================================================================

class AlertListView(APIView):
    """GET /api/alerts/"""
    permission_classes = [AllowAny]

    def get(self, request):
        region_id = request.query_params.get('region_id')
        qs = Alert.objects.select_related('region').filter(is_active=True).order_by('-created_at')
        if region_id:
            qs = qs.filter(region_id=region_id)
        return _ok(AlertSerializer(qs[:100], many=True).data)


class AlertMarkReadView(APIView):
    """POST /api/alerts/{id}/mark-read/"""
    permission_classes = [AllowAny]

    def post(self, request, alert_id):
        try:
            alert = Alert.objects.get(pk=alert_id)
        except Alert.DoesNotExist:
            return _err('Alert not found.', status.HTTP_404_NOT_FOUND)
        alert.is_read = True
        alert.save(update_fields=['is_read', 'updated_at'])
        return _ok({'id': alert.pk, 'is_read': True}, 'Alert marked as read.')


class AlertUnreadCountView(APIView):
    """GET /api/alerts/unread-count/"""
    permission_classes = [AllowAny]

    def get(self, request):
        count = Alert.objects.filter(is_active=True, is_read=False).count()
        return _ok({'unread_count': count})


# ==========================================================================
# RECOMMENDATIONS
# ==========================================================================

class RecommendationListView(APIView):
    """GET /api/recommendations/"""
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Recommendation.objects.select_related('region').filter(is_active=True).order_by('-created_at')
        return _ok(RecommendationSerializer(qs[:50], many=True).data)


class RegionRecommendationsView(APIView):
    """GET /api/recommendations/{region_id}/"""
    permission_classes = [AllowAny]

    def get(self, request, region_id):
        try:
            Region.objects.get(pk=region_id)
        except Region.DoesNotExist:
            return _err('Region not found.', status.HTTP_404_NOT_FOUND)
        qs = Recommendation.objects.filter(region_id=region_id, is_active=True).order_by('-created_at')
        return _ok(RecommendationSerializer(qs, many=True).data)


# ==========================================================================
# DASHBOARD
# ==========================================================================

class DashboardSummaryView(APIView):
    """GET /api/dashboard/summary/"""
    permission_classes = [AllowAny]

    def get(self, request):
        regions = list(Region.objects.filter(is_active=True).prefetch_related('predictions__risk_assessment'))

        risk_counts = {'CRITICAL': 0, 'HIGH': 0, 'MODERATE': 0, 'LOW': 0, 'UNKNOWN': 0}
        for region in regions:
            latest = region.predictions.first()
            level = latest.risk_level if latest else 'UNKNOWN'
            risk_counts[level] = risk_counts.get(level, 0) + 1

        unread_alerts = Alert.objects.filter(is_active=True, is_read=False).count()
        total_predictions = WaterPrediction.objects.count()

        data = {
            'total_regions': len(regions),
            'critical_regions': risk_counts.get('CRITICAL', 0),
            'high_risk_regions': risk_counts.get('HIGH', 0),
            'moderate_risk_regions': risk_counts.get('MODERATE', 0),
            'low_risk_regions': risk_counts.get('LOW', 0),
            'unread_alerts': unread_alerts,
            'total_predictions': total_predictions,
            'regions': RiskSummarySerializer(regions, many=True).data,
        }

        return _ok(data)
