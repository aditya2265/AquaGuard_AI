from django.db import models


class WaterMeasurement(models.Model):
    region = models.ForeignKey(
        'regions.Region',
        on_delete=models.CASCADE,
        related_name='water_measurements',
    )
    date = models.DateField()
    reservoir_level = models.FloatField(help_text='Reservoir fill percentage (0-100)')
    reservoir_capacity_mcm = models.FloatField(help_text='Total reservoir capacity in million cubic meters')
    current_storage_mcm = models.FloatField(help_text='Current storage in million cubic meters')
    rainfall_mm = models.FloatField(help_text='Daily rainfall in millimeters')
    water_consumption_mld = models.FloatField(help_text='Water consumption in million litres per day')
    groundwater_level_m = models.FloatField(help_text='Groundwater level in meters below ground')
    inflow_mcm = models.FloatField(help_text='Daily inflow in million cubic meters')
    outflow_mcm = models.FloatField(help_text='Daily outflow in million cubic meters')
    is_demo_data = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Water Measurement'
        verbose_name_plural = 'Water Measurements'
        ordering = ['-date']
        unique_together = ('region', 'date')

    def __str__(self):
        return f'{self.region.name} - {self.date} ({self.reservoir_level:.1f}%)'

    @property
    def net_flow_mcm(self):
        return self.inflow_mcm - self.outflow_mcm


class WeatherMeasurement(models.Model):
    region = models.ForeignKey(
        'regions.Region',
        on_delete=models.CASCADE,
        related_name='weather_measurements',
    )
    date = models.DateField()
    temperature_celsius = models.FloatField()
    humidity_percent = models.FloatField()
    wind_speed_kmh = models.FloatField()
    is_demo_data = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Weather Measurement'
        verbose_name_plural = 'Weather Measurements'
        ordering = ['-date']
        unique_together = ('region', 'date')

    def __str__(self):
        return f'{self.region.name} - {self.date} ({self.temperature_celsius:.1f}°C)'
