from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from rest_framework import generics, permissions
from .models import WaterMeasurement, WeatherMeasurement
from .forms import CSVImportForm
from .serializers import WaterMeasurementSerializer, WeatherMeasurementSerializer
from .csv_import import import_csv


class DataImportView(View):
    template_name = 'water_data/import.html'

    def get(self, request):
        form = CSVImportForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            success_count, errors = import_csv(csv_file, is_demo_data=False)
            if errors:
                for err in errors[:20]:  # limit displayed errors
                    messages.warning(request, err)
                if len(errors) > 20:
                    messages.warning(request, f'... and {len(errors) - 20} more errors.')
            if success_count:
                messages.success(request, f'Successfully imported {success_count} record(s).')
            else:
                messages.error(request, 'No records were imported. Please check your CSV file.')
        return render(request, self.template_name, {'form': form})


class WaterDataListView(View):
    template_name = 'water_data/list.html'

    def get(self, request):
        region_id = request.GET.get('region')
        measurements = WaterMeasurement.objects.select_related('region').order_by('-date')
        if region_id:
            measurements = measurements.filter(region_id=region_id)
        measurements = measurements[:200]
        return render(request, self.template_name, {'measurements': measurements})


# DRF API Views
class WaterMeasurementAPIListView(generics.ListAPIView):
    serializer_class = WaterMeasurementSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = WaterMeasurement.objects.select_related('region').order_by('-date')
        region_id = self.request.query_params.get('region')
        if region_id:
            qs = qs.filter(region_id=region_id)
        return qs


class WeatherMeasurementAPIListView(generics.ListAPIView):
    serializer_class = WeatherMeasurementSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = WeatherMeasurement.objects.select_related('region').order_by('-date')
        region_id = self.request.query_params.get('region')
        if region_id:
            qs = qs.filter(region_id=region_id)
        return qs
