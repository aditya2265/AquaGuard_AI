from django.db import models


class WaterPrediction(models.Model):
    RISK_LEVEL_CHOICES = [
        ('LOW', 'Low'),
        ('MODERATE', 'Moderate'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    HORIZON_CHOICES = [
        (7, '7 Days'),
        (14, '14 Days'),
        (30, '30 Days'),
    ]

    region = models.ForeignKey(
        'regions.Region',
        on_delete=models.CASCADE,
        related_name='predictions',
    )
    prediction_date = models.DateTimeField(auto_now_add=True)
    horizon_days = models.IntegerField(choices=HORIZON_CHOICES, default=7)
    risk_probability = models.FloatField(help_text='Risk probability 0.0 to 1.0')
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='LOW')
    predicted_reservoir_level = models.FloatField(help_text='Predicted reservoir level (%)')
    predicted_consumption = models.FloatField(help_text='Predicted daily consumption (MLD)')
    expected_shortage_start = models.DateField(null=True, blank=True)
    model_version = models.CharField(max_length=50, default='1.0.0')
    is_demo = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Water Prediction'
        verbose_name_plural = 'Water Predictions'
        ordering = ['-prediction_date']

    def __str__(self):
        return f'{self.region.name} - {self.risk_level} ({self.horizon_days}d) @ {self.prediction_date.date()}'

    @property
    def risk_color(self):
        colors = {'LOW': 'success', 'MODERATE': 'warning', 'HIGH': 'danger', 'CRITICAL': 'dark'}
        return colors.get(self.risk_level, 'secondary')


class RiskAssessment(models.Model):
    prediction = models.OneToOneField(
        WaterPrediction,
        on_delete=models.CASCADE,
        related_name='risk_assessment',
    )
    risk_score = models.FloatField(help_text='Composite risk score 0-100')
    rainfall_factor = models.FloatField(default=0.0)
    reservoir_factor = models.FloatField(default=0.0)
    consumption_factor = models.FloatField(default=0.0)
    temperature_factor = models.FloatField(default=0.0)
    demand_factor = models.FloatField(default=0.0)
    contributing_factors = models.JSONField(
        default=dict,
        help_text='Dict of factor name to delta percentage',
    )
    explanation_text = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Risk Assessment'
        verbose_name_plural = 'Risk Assessments'

    def __str__(self):
        return f'Assessment for {self.prediction} (score={self.risk_score:.1f})'
