from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    latitude = models.FloatField()
    longitude = models.FloatField()
    population = models.IntegerField(default=0)
    area_sq_km = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'
        ordering = ['name']

    def __str__(self):
        return f'{self.name}, {self.state}'
