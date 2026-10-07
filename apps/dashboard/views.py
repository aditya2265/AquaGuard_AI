import json
import os
from datetime import datetime, timedelta
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from apps.regions.models import Region
from apps.water_data.models import WaterMeasurement
from apps.predictions.models import WaterPrediction
from apps.alerts.models import Alert
from apps.recommendations.models import Recommendation


class DashboardView(View):
    template_name = 'dashboard/dashboard.html'

    def get(self, request):
        regions = Region.objects.filter(is_active=True)

        # Latest measurement + prediction per region
        latest_measurements = {}
        latest_predictions = {}
        for region in regions:
            m = WaterMeasurement.objects.filter(region=region).order_by('-date').first()
            if m:
                latest_measurements[region.pk] = m
            p = WaterPrediction.objects.filter(region=region).order_by('-prediction_date').first()
            if p:
                latest_predictions[region.pk] = p

        # Region overview for table (sorted by risk)
        risk_order = {'CRITICAL': 0, 'HIGH': 1, 'MODERATE': 2, 'LOW': 3, None: 4}
        region_overview = []
        for region in regions:
            m = latest_measurements.get(region.pk)
            p = latest_predictions.get(region.pk)
            region_overview.append({'region': region, 'measurement': m, 'prediction': p})
        region_overview.sort(key=lambda x: risk_order.get(x['prediction'].risk_level if x['prediction'] else None, 4))

        # Risk distribution
        risk_distribution = {'LOW': 0, 'MODERATE': 0, 'HIGH': 0, 'CRITICAL': 0}
        for item in region_overview:
            if item['prediction']:
                lvl = item['prediction'].risk_level
                if lvl in risk_distribution:
                    risk_distribution[lvl] += 1

        # Average risk probability across all regions
        probs = [item['prediction'].risk_probability * 100 for item in region_overview if item['prediction']]
        avg_risk_probability = sum(probs) / len(probs) if probs else 0

        # Dominant risk level
        dominant_risk_level = None
        for level in ['CRITICAL', 'HIGH', 'MODERATE', 'LOW']:
            if risk_distribution[level] > 0:
                dominant_risk_level = level
                break

        # 30-day trend data
        today = timezone.now().date()
        trend_labels = []
        trend_data = []
        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            preds_on_day = WaterPrediction.objects.filter(prediction_date__date=day)
            if preds_on_day.exists():
                avg = sum(p.risk_probability for p in preds_on_day) / preds_on_day.count() * 100
            else:
                avg = 0
            trend_labels.append(day.strftime('%b %d'))
            trend_data.append(round(avg, 1))

        # If no real trend data, use demo values
        if sum(trend_data) == 0:
            import random
            random.seed(42)
            base = 35
            trend_data = []
            for i in range(30):
                base += random.uniform(-5, 8)
                base = max(10, min(80, base))
                trend_data.append(round(base, 1))

        # Predictions today
        predictions_today = WaterPrediction.objects.filter(
            prediction_date__date=today
        ).count()

        # Unread alerts
        unread_alert_count = Alert.objects.filter(is_active=True, is_read=False).count()
        critical_count = Alert.objects.filter(is_active=True, severity='CRITICAL').count()
        total_alerts = Alert.objects.filter(is_active=True).count()

        # Recent unread alerts
        recent_alerts = (
            Alert.objects.filter(is_active=True, is_read=False)
            .select_related('region')
            .order_by('-created_at')[:5]
        )

        # Recent active recommendations
        recent_recommendations = (
            Recommendation.objects.filter(is_active=True)
            .select_related('region')
            .order_by('-created_at')[:5]
        )

        # Build geo JSON for map
        regions_geo = []
        for item in region_overview:
            r = item['region']
            p = item['prediction']
            m = item['measurement']
            regions_geo.append({
                'id': r.pk,
                'name': r.name,
                'state': r.state,
                'lat': r.latitude,
                'lng': r.longitude,
                'risk_level': p.risk_level if p else 'LOW',
                'risk_probability': p.risk_probability if p else 0,
                'reservoir_level': m.reservoir_level if m else None,
                'rainfall_mm': m.rainfall_mm if m else None,
            })

        context = {
            'regions': regions,
            'region_overview': region_overview,
            'risk_distribution': json.dumps(risk_distribution),
            'avg_risk_probability': avg_risk_probability,
            'dominant_risk_level': dominant_risk_level,
            'trend_labels': json.dumps(trend_labels),
            'trend_data': json.dumps(trend_data),
            'unread_alert_count': unread_alert_count,
            'critical_count': critical_count,
            'total_alerts': total_alerts,
            'total_regions': regions.count(),
            'predictions_today': predictions_today,
            'recent_alerts': recent_alerts,
            'recent_recommendations': recent_recommendations,
            'regions_geo_json': json.dumps(regions_geo),
        }
        return render(request, self.template_name, context)


class SettingsView(View):
    template_name = 'dashboard/settings.html'

    def get(self, request):
        # IBM config check (only presence, not values)
        ibm_api_key_set = bool(os.environ.get('IBM_API_KEY', '').strip())
        ibm_project_id_set = bool(os.environ.get('IBM_PROJECT_ID', '').strip())
        ibm_url_set = bool(os.environ.get('IBM_URL', '').strip())
        ibm_active = ibm_api_key_set and ibm_project_id_set and ibm_url_set

        # DB counts
        total_regions = Region.objects.filter(is_active=True).count()
        total_predictions = WaterPrediction.objects.count()
        total_measurements = WaterMeasurement.objects.count()
        has_demo_data = WaterMeasurement.objects.filter(is_demo_data=True).exists()

        # ML model file check
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base_dir, 'ml', 'models', 'risk_classifier.joblib')
        ml_model_trained = os.path.isfile(model_path)

        context = {
            'ibm_active': ibm_active,
            'ibm_api_key_set': ibm_api_key_set,
            'ibm_project_id_set': ibm_project_id_set,
            'ibm_url_set': ibm_url_set,
            'total_regions': total_regions,
            'total_predictions': total_predictions,
            'total_measurements': total_measurements,
            'has_demo_data': has_demo_data,
            'ml_model_trained': ml_model_trained,
        }
        return render(request, self.template_name, context)
