"""
URL patterns for the consolidated AquaGuard REST API.
All routes are mounted under /api/ in config/urls.py.
"""
from django.urls import path
from apps.api import views

urlpatterns = [
    # Regions
    path('regions/', views.RegionListView.as_view(), name='api-regions-list'),
    path('regions/<int:region_id>/', views.RegionDetailView.as_view(), name='api-regions-detail'),
    path('regions/<int:region_id>/predictions/', views.RegionPredictionsView.as_view(), name='api-regions-predictions'),
    path('regions/<int:region_id>/latest-measurements/', views.RegionLatestMeasurementsView.as_view(), name='api-regions-latest-measurements'),
    path('regions/<int:region_id>/run-prediction/', views.RunPredictionView.as_view(), name='api-regions-run-prediction'),

    # Water / weather data
    path('water-data/', views.WaterDataListView.as_view(), name='api-water-data-list'),
    path('weather-data/', views.WeatherDataListView.as_view(), name='api-weather-data-list'),

    # Predictions
    path('predictions/', views.PredictionListView.as_view(), name='api-predictions-list'),
    path('predictions/<int:prediction_id>/', views.PredictionDetailView.as_view(), name='api-predictions-detail'),
    path('predictions/<int:prediction_id>/explanation/', views.PredictionExplanationView.as_view(), name='api-predictions-explanation'),

    # Risk
    path('risk/summary/', views.RiskSummaryView.as_view(), name='api-risk-summary'),
    path('risk/<int:region_id>/', views.RegionRiskView.as_view(), name='api-risk-region'),

    # Alerts
    path('alerts/', views.AlertListView.as_view(), name='api-alerts-list'),
    path('alerts/unread-count/', views.AlertUnreadCountView.as_view(), name='api-alerts-unread-count'),
    path('alerts/<int:alert_id>/mark-read/', views.AlertMarkReadView.as_view(), name='api-alerts-mark-read'),

    # Recommendations
    path('recommendations/', views.RecommendationListView.as_view(), name='api-recommendations-list'),
    path('recommendations/<int:region_id>/', views.RegionRecommendationsView.as_view(), name='api-recommendations-region'),

    # Dashboard
    path('dashboard/summary/', views.DashboardSummaryView.as_view(), name='api-dashboard-summary'),
]
