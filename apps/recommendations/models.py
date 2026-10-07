from django.db import models


class Recommendation(models.Model):
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    CATEGORY_CHOICES = [
        ('conservation', 'Conservation'),
        ('supply', 'Supply Management'),
        ('monitoring', 'Monitoring'),
        ('planning', 'Planning'),
    ]

    region = models.ForeignKey(
        'regions.Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommendations',
    )
    prediction = models.ForeignKey(
        'predictions.WaterPrediction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommendations',
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='conservation')
    title = models.CharField(max_length=200)
    description = models.TextField()
    action_required = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Recommendation'
        verbose_name_plural = 'Recommendations'
        ordering = ['-created_at']

    def __str__(self):
        region_name = self.region.name if self.region else 'Global'
        return f'[{self.priority}] {self.title} ({region_name})'

    @property
    def priority_color(self):
        colors = {'LOW': 'info', 'MEDIUM': 'warning', 'HIGH': 'danger', 'CRITICAL': 'dark'}
        return colors.get(self.priority, 'secondary')
