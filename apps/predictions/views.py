import json
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import JsonResponse
from rest_framework import generics, permissions
from apps.regions.models import Region
from apps.water_data.models import WaterMeasurement
from .models import WaterPrediction, RiskAssessment
from .serializers import WaterPredictionSerializer


class PredictionListView(View):
    """Main prediction page — renders prediction.html"""
    template_name = 'predictions/prediction.html'

    def get(self, request):
        regions = Region.objects.filter(is_active=True).order_by('name')
        region_id = request.GET.get('region')
        selected_horizon = int(request.GET.get('horizon', 7))

        selected_region = None
        latest_prediction = None
        risk_assessment = None
        latest_measurement = None
        all_predictions = []

        # Prediction chart data
        pred_horizons = []
        pred_probabilities = []

        # Historical chart data (60 days)
        hist_dates = []
        hist_reservoir = []
        hist_rainfall = []

        if region_id:
            try:
                selected_region = Region.objects.get(pk=region_id, is_active=True)
            except Region.DoesNotExist:
                selected_region = None

        if selected_region:
            # Latest prediction
            latest_prediction = (
                WaterPrediction.objects
                .filter(region=selected_region)
                .order_by('-prediction_date')
                .first()
            )

            # Risk assessment
            if latest_prediction:
                try:
                    risk_assessment = latest_prediction.risk_assessment
                except RiskAssessment.DoesNotExist:
                    risk_assessment = None

            # Predictions for all 3 horizons (latest per horizon)
            for horizon in [7, 14, 30]:
                p = (
                    WaterPrediction.objects
                    .filter(region=selected_region, horizon_days=horizon)
                    .order_by('-prediction_date')
                    .first()
                )
                if p:
                    pred_horizons.append(horizon)
                    pred_probabilities.append(round(p.risk_probability * 100, 1))

            if not pred_horizons:
                pred_horizons = [7, 14, 30]
                pred_probabilities = [0, 0, 0]

            # All predictions for this region
            all_predictions = (
                WaterPrediction.objects
                .filter(region=selected_region)
                .order_by('-prediction_date')[:20]
            )

            # Latest measurement
            latest_measurement = (
                WaterMeasurement.objects
                .filter(region=selected_region)
                .order_by('-date')
                .first()
            )

            # Historical data (60 days)
            hist_measurements = (
                WaterMeasurement.objects
                .filter(region=selected_region)
                .order_by('date')
                .values('date', 'reservoir_level', 'rainfall_mm')
            )
            for m in hist_measurements:
                hist_dates.append(m['date'].strftime('%b %d'))
                hist_reservoir.append(round(float(m['reservoir_level']), 1))
                hist_rainfall.append(round(float(m['rainfall_mm']), 1))

        context = {
            'regions': regions,
            'selected_region': selected_region,
            'selected_horizon': selected_horizon,
            'latest_prediction': latest_prediction,
            'risk_assessment': risk_assessment,
            'latest_measurement': latest_measurement,
            'all_predictions': all_predictions,
            'pred_horizons': json.dumps(pred_horizons),
            'pred_probabilities': json.dumps(pred_probabilities),
            'hist_dates': json.dumps(hist_dates),
            'hist_reservoir': json.dumps(hist_reservoir),
            'hist_rainfall': json.dumps(hist_rainfall),
        }
        return render(request, self.template_name, context)


class PredictionDetailView(View):
    """AI Explanation detail page"""
    template_name = 'predictions/ai_explanation.html'

    def get(self, request, pk):
        prediction = get_object_or_404(
            WaterPrediction.objects.select_related('region'),
            pk=pk,
        )
        try:
            assessment = prediction.risk_assessment
        except RiskAssessment.DoesNotExist:
            assessment = None
        return render(request, self.template_name, {
            'prediction': prediction,
            'assessment': assessment,
        })


class AIExplanationView(View):
    """Returns AI-generated explanation as JSON for API callers."""

    def get(self, request, pk):
        prediction = get_object_or_404(WaterPrediction, pk=pk)
        try:
            assessment = prediction.risk_assessment
            explanation = assessment.explanation_text
        except RiskAssessment.DoesNotExist:
            explanation = 'No explanation available for this prediction.'
        return JsonResponse({
            'prediction_id': prediction.pk,
            'region': prediction.region.name,
            'risk_level': prediction.risk_level,
            'explanation': explanation,
        })


# DRF API
class PredictionAPIListView(generics.ListAPIView):
    serializer_class = WaterPredictionSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = WaterPrediction.objects.select_related('region').order_by('-prediction_date')
        region_id = self.request.query_params.get('region')
        if region_id:
            qs = qs.filter(region_id=region_id)
        return qs


class PredictionAPIDetailView(generics.RetrieveAPIView):
    queryset = WaterPrediction.objects.select_related('region')
    serializer_class = WaterPredictionSerializer
    permission_classes = [permissions.AllowAny]
