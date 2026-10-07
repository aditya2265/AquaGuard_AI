import json
from django.shortcuts import render, get_object_or_404
from django.views import View
from rest_framework import generics, permissions
from apps.water_data.models import WaterMeasurement
from apps.predictions.models import WaterPrediction
from apps.alerts.models import Alert
from apps.recommendations.models import Recommendation
from .models import Region
from .serializers import RegionSerializer


class RegionListView(View):
    template_name = 'regions/region_list.html'

    def get(self, request):
        regions = Region.objects.filter(is_active=True).order_by('name')

        # Apply search filter
        search = request.GET.get('search', '').strip()
        risk_filter = request.GET.get('risk', '')
        if search:
            regions = regions.filter(name__icontains=search)

        latest_measurements = {}
        latest_predictions = {}
        for region in regions:
            m = WaterMeasurement.objects.filter(region=region).order_by('-date').first()
            if m:
                latest_measurements[region.pk] = m
            p = WaterPrediction.objects.filter(region=region).order_by('-prediction_date').first()
            if p:
                latest_predictions[region.pk] = p

        regions_data = []
        for region in regions:
            m = latest_measurements.get(region.pk)
            p = latest_predictions.get(region.pk)
            if risk_filter and (not p or p.risk_level != risk_filter):
                continue
            regions_data.append({'region': region, 'measurement': m, 'prediction': p})

        # Sort by risk (CRITICAL first)
        risk_order = {'CRITICAL': 0, 'HIGH': 1, 'MODERATE': 2, 'LOW': 3, None: 4}
        regions_data.sort(
            key=lambda x: risk_order.get(x['prediction'].risk_level if x['prediction'] else None, 4)
        )

        # Summary metrics
        probs = [item['prediction'].risk_probability * 100 for item in regions_data if item['prediction']]
        avg_risk = sum(probs) / len(probs) if probs else 0
        highest_risk_region = None
        if regions_data and regions_data[0]['prediction']:
            highest_risk_region = regions_data[0]['region'].name

        return render(request, self.template_name, {
            'regions_data': regions_data,
            'total_regions': Region.objects.filter(is_active=True).count(),
            'avg_risk': avg_risk,
            'highest_risk_region': highest_risk_region,
        })


class RegionDetailView(View):
    template_name = 'regions/region_detail.html'

    def get(self, request, pk):
        region = get_object_or_404(Region, pk=pk)

        # Latest measurement
        latest_measurement = (
            WaterMeasurement.objects.filter(region=region).order_by('-date').first()
        )

        # Latest prediction
        latest_prediction = (
            WaterPrediction.objects.filter(region=region).order_by('-prediction_date').first()
        )

        # Recent predictions (one per horizon)
        predictions = []
        for horizon in [7, 14, 30]:
            p = WaterPrediction.objects.filter(region=region, horizon_days=horizon).order_by('-prediction_date').first()
            if p:
                predictions.append(p)

        # Recommendations
        recommendations = (
            Recommendation.objects.filter(region=region, is_active=True).order_by('-created_at')[:5]
        )

        # Alerts
        alerts = Alert.objects.filter(region=region, is_active=True).order_by('-created_at')[:5]

        # Historical chart data (30 days)
        hist_measurements = (
            WaterMeasurement.objects.filter(region=region)
            .order_by('date')
            .values('date', 'reservoir_level', 'rainfall_mm')
        )
        hist_dates = []
        hist_reservoir = []
        hist_rainfall = []
        for m in hist_measurements:
            hist_dates.append(m['date'].strftime('%b %d'))
            hist_reservoir.append(round(float(m['reservoir_level']), 1))
            hist_rainfall.append(round(float(m['rainfall_mm']), 1))

        return render(request, self.template_name, {
            'region': region,
            'latest_measurement': latest_measurement,
            'latest_prediction': latest_prediction,
            'predictions': predictions,
            'recommendations': recommendations,
            'alerts': alerts,
            'hist_dates': json.dumps(hist_dates),
            'hist_reservoir': json.dumps(hist_reservoir),
            'hist_rainfall': json.dumps(hist_rainfall),
        })


class MapView(View):
    """Full-page water risk map"""
    template_name = 'regions/map.html'

    def get(self, request):
        regions = Region.objects.filter(is_active=True)
        regions_data = []
        regions_geo = []

        for region in regions:
            p = WaterPrediction.objects.filter(region=region).order_by('-prediction_date').first()
            m = WaterMeasurement.objects.filter(region=region).order_by('-date').first()
            regions_data.append({'region': region, 'prediction': p, 'measurement': m})
            regions_geo.append({
                'id': region.pk,
                'name': region.name,
                'state': region.state,
                'lat': region.latitude,
                'lng': region.longitude,
                'risk_level': p.risk_level if p else 'LOW',
                'risk_probability': p.risk_probability if p else 0,
                'reservoir_level': m.reservoir_level if m else None,
                'rainfall_mm': m.rainfall_mm if m else None,
            })

        return render(request, self.template_name, {
            'regions_data': regions_data,
            'regions_geo_json': json.dumps(regions_geo),
        })


class RegionComparisonView(View):
    template_name = 'regions/comparison.html'

    def get(self, request):
        regions = Region.objects.filter(is_active=True).order_by('name')
        selected_ids = request.GET.getlist('region')
        selected_regions = []
        if selected_ids:
            selected_regions = Region.objects.filter(pk__in=selected_ids, is_active=True)
        return render(request, self.template_name, {
            'regions': regions,
            'selected_regions': selected_regions,
        })


# DRF API Views
class RegionAPIListView(generics.ListAPIView):
    queryset = Region.objects.filter(is_active=True)
    serializer_class = RegionSerializer
    permission_classes = [permissions.AllowAny]


class RegionAPIDetailView(generics.RetrieveAPIView):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [permissions.AllowAny]
