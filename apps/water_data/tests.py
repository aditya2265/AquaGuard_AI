import io
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from apps.regions.models import Region
from .models import WaterMeasurement, WeatherMeasurement
from .csv_import import import_csv


def make_region(name='Import Region'):
    return Region.objects.create(
        name=name,
        state='Test State',
        latitude=12.0,
        longitude=77.0,
    )


class WaterMeasurementTest(TestCase):
    def setUp(self):
        self.region = make_region()

    def test_measurement_creation(self):
        m = WaterMeasurement.objects.create(
            region=self.region,
            date=date(2024, 1, 15),
            reservoir_level=65.0,
            reservoir_capacity_mcm=1000.0,
            current_storage_mcm=650.0,
            rainfall_mm=5.0,
            water_consumption_mld=200.0,
            groundwater_level_m=10.0,
            inflow_mcm=8.0,
            outflow_mcm=6.0,
        )
        self.assertEqual(m.reservoir_level, 65.0)
        self.assertFalse(m.is_demo_data)

    def test_measurement_str(self):
        m = WaterMeasurement.objects.create(
            region=self.region,
            date=date(2024, 1, 15),
            reservoir_level=65.0,
            reservoir_capacity_mcm=1000.0,
            current_storage_mcm=650.0,
            rainfall_mm=5.0,
            water_consumption_mld=200.0,
            groundwater_level_m=10.0,
            inflow_mcm=8.0,
            outflow_mcm=6.0,
        )
        self.assertIn('Import Region', str(m))
        self.assertIn('65.0', str(m))

    def test_net_flow_property(self):
        m = WaterMeasurement(inflow_mcm=10.0, outflow_mcm=6.0)
        self.assertAlmostEqual(m.net_flow_mcm, 4.0)

    def test_unique_together(self):
        from django.db import IntegrityError
        WaterMeasurement.objects.create(
            region=self.region, date=date(2024, 2, 1),
            reservoir_level=50.0, reservoir_capacity_mcm=1000.0,
            current_storage_mcm=500.0, rainfall_mm=2.0,
            water_consumption_mld=100.0, groundwater_level_m=8.0,
            inflow_mcm=5.0, outflow_mcm=4.0,
        )
        with self.assertRaises(IntegrityError):
            WaterMeasurement.objects.create(
                region=self.region, date=date(2024, 2, 1),
                reservoir_level=60.0, reservoir_capacity_mcm=1000.0,
                current_storage_mcm=600.0, rainfall_mm=3.0,
                water_consumption_mld=110.0, groundwater_level_m=9.0,
                inflow_mcm=6.0, outflow_mcm=4.0,
            )


class CSVImportTest(TestCase):
    def setUp(self):
        self.region = make_region('CSV Test City')

    def _make_csv(self, rows):
        header = (
            'date,region,rainfall_mm,temperature_celsius,humidity_percent,'
            'reservoir_level,water_consumption_mld,groundwater_level_m,inflow_mcm,outflow_mcm'
        )
        lines = [header] + rows
        return '\n'.join(lines)

    def test_valid_csv_import(self):
        csv_data = self._make_csv([
            '2024-03-01,CSV Test City,10.5,28.0,60.0,70.0,150.0,12.0,8.0,6.0',
            '2024-03-02,CSV Test City,0.0,30.0,55.0,68.0,155.0,11.5,7.0,6.5',
        ])
        count, errors = import_csv(csv_data, is_demo_data=False)
        self.assertEqual(count, 2)
        self.assertEqual(errors, [])

    def test_missing_columns_error(self):
        bad_csv = 'date,region\n2024-01-01,CSV Test City\n'
        count, errors = import_csv(bad_csv)
        self.assertEqual(count, 0)
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any('missing' in e.lower() for e in errors))

    def test_invalid_date_error(self):
        csv_data = self._make_csv([
            'not-a-date,CSV Test City,10.0,28.0,60.0,70.0,150.0,12.0,8.0,6.0',
        ])
        count, errors = import_csv(csv_data)
        self.assertEqual(count, 0)
        self.assertTrue(len(errors) > 0)

    def test_invalid_numeric_error(self):
        csv_data = self._make_csv([
            '2024-04-01,CSV Test City,abc,28.0,60.0,70.0,150.0,12.0,8.0,6.0',
        ])
        count, errors = import_csv(csv_data)
        self.assertEqual(count, 0)
        self.assertTrue(len(errors) > 0)

    def test_unknown_region_error(self):
        csv_data = self._make_csv([
            '2024-05-01,NonExistentCity,5.0,25.0,60.0,70.0,100.0,10.0,5.0,4.0',
        ])
        count, errors = import_csv(csv_data)
        self.assertEqual(count, 0)
        self.assertTrue(len(errors) > 0)
