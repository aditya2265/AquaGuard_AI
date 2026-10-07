from django.db import models
from django.contrib.auth.models import User


class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('water_summary', 'Water Summary'),
        ('risk_analysis', 'Risk Analysis'),
        ('prediction_report', 'Prediction Report'),
        ('regional_comparison', 'Regional Comparison'),
        ('monthly_overview', 'Monthly Overview'),
    ]

    region = models.ForeignKey(
        'regions.Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reports',
    )
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES, default='water_summary')
    file_path = models.FileField(upload_to='reports/', null=True, blank=True)
    summary = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    parameters = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
        ordering = ['-generated_at']

    def __str__(self):
        region_name = self.region.name if self.region else 'All Regions'
        return f'{self.title} ({region_name}) - {self.generated_at.date()}'
