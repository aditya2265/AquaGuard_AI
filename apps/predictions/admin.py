from django.contrib import admin
from .models import WaterPrediction, RiskAssessment


class RiskAssessmentInline(admin.StackedInline):
    model = RiskAssessment
    can_delete = False
    readonly_fields = ('generated_at',)
    extra = 0


@admin.register(WaterPrediction)
class WaterPredictionAdmin(admin.ModelAdmin):
    list_display = (
        'region', 'risk_level', 'risk_probability', 'horizon_days',
        'predicted_reservoir_level', 'prediction_date', 'is_demo',
    )
    list_filter = ('risk_level', 'horizon_days', 'is_demo', 'region')
    search_fields = ('region__name',)
    readonly_fields = ('prediction_date',)
    ordering = ('-prediction_date',)
    inlines = [RiskAssessmentInline]


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ('prediction', 'risk_score', 'generated_at')
    readonly_fields = ('generated_at',)
    search_fields = ('prediction__region__name',)
