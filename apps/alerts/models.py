from django.db import models


class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    ALERT_TYPE_CHOICES = [
        ('reservoir', 'Reservoir Level'),
        ('rainfall', 'Rainfall'),
        ('consumption', 'Consumption'),
        ('prediction', 'Prediction Based'),
        ('groundwater', 'Groundwater'),
        ('general', 'General'),
    ]

    region = models.ForeignKey(
        'regions.Region',
        on_delete=models.CASCADE,
        related_name='alerts',
    )
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='INFO')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.severity}] {self.title} - {self.region.name}'

    @property
    def severity_color(self):
        colors = {'INFO': 'info', 'WARNING': 'warning', 'HIGH': 'danger', 'CRITICAL': 'dark'}
        return colors.get(self.severity, 'secondary')
