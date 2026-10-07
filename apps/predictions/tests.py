from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from apps.regions.models import Region
from ml.risk_engine import (
    calculate_risk_score,
    get_risk_level,
    get_risk_color,
    generate_explanation,
)
from .models import WaterPrediction, RiskAssessment


def make_region(name='Pred Region'):
    return Region.objects.create(
        name=name, state='Test State', latitude=12.0, longitude=77.0
    )


class RiskEngineTest(TestCase):

    def _score(self, reservoir, rainfall, rainfall_avg=5.0,
               consumption=100.0, consumption_avg=100.0,
               temperature=25.0, temperature_avg=25.0):
        return calculate_risk_score(
            reservoir_level=reservoir,
            rainfall_mm=rainfall,
            rainfall_avg=rainfall_avg,
            consumption_mld=consumption,
            consumption_avg=consumption_avg,
            temperature=temperature,
            temperature_avg=temperature_avg,
        )

    def test_risk_score_low(self):
        # Full reservoir, rainfall above average, consumption on target, neutral temperature
        result = self._score(
            reservoir=95.0, rainfall=15.0, rainfall_avg=10.0,
            consumption=95.0, consumption_avg=100.0,
            temperature=25.0, temperature_avg=25.0,
        )
        self.assertLessEqual(result['score'], 25.0)
        self.assertEqual(result['level'], 'LOW')

    def test_risk_score_critical(self):
        result = self._score(reservoir=5.0, rainfall=0.0, rainfall_avg=20.0,
                             consumption=200.0, consumption_avg=100.0,
                             temperature=40.0, temperature_avg=25.0)
        self.assertGreaterEqual(result['score'], 76.0)
        self.assertEqual(result['level'], 'CRITICAL')

    def test_risk_level_boundaries(self):
        self.assertEqual(get_risk_level(0),   'LOW')
        self.assertEqual(get_risk_level(25),  'LOW')
        self.assertEqual(get_risk_level(26),  'MODERATE')
        self.assertEqual(get_risk_level(50),  'MODERATE')
        self.assertEqual(get_risk_level(51),  'HIGH')
        self.assertEqual(get_risk_level(75),  'HIGH')
        self.assertEqual(get_risk_level(76),  'CRITICAL')
        self.assertEqual(get_risk_level(100), 'CRITICAL')

    def test_explanation_generated(self):
        result = self._score(reservoir=30.0, rainfall=2.0, rainfall_avg=10.0)
        explanation = generate_explanation(result['factors'], result['level'])
        self.assertIsInstance(explanation, str)
        self.assertGreater(len(explanation), 20)
        self.assertIn(result['level'], explanation)

    def test_score_structure(self):
        result = self._score(reservoir=50.0, rainfall=5.0)
        self.assertIn('score', result)
        self.assertIn('level', result)
        self.assertIn('probability', result)
        self.assertIn('factors', result)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)
        self.assertGreaterEqual(result['probability'], 0.0)
        self.assertLessEqual(result['probability'], 1.0)

    def test_probability_matches_score(self):
        result = self._score(reservoir=50.0, rainfall=5.0)
        self.assertAlmostEqual(result['probability'], result['score'] / 100.0, places=3)


class RiskColorTest(TestCase):
    def test_risk_colors(self):
        self.assertEqual(get_risk_color('LOW'), '#22c55e')
        self.assertEqual(get_risk_color('MODERATE'), '#f59e0b')
        self.assertEqual(get_risk_color('HIGH'), '#f97316')
        self.assertEqual(get_risk_color('CRITICAL'), '#ef4444')

    def test_unknown_risk_color(self):
        color = get_risk_color('UNKNOWN')
        self.assertIsInstance(color, str)
        self.assertTrue(color.startswith('#'))


class PredictionModelTest(TestCase):
    def setUp(self):
        self.region = make_region('Pred Model Region')

    def test_prediction_creation(self):
        pred = WaterPrediction.objects.create(
            region=self.region,
            horizon_days=7,
            risk_probability=0.65,
            risk_level='HIGH',
            predicted_reservoir_level=35.0,
            predicted_consumption=200.0,
        )
        self.assertEqual(pred.risk_level, 'HIGH')
        self.assertAlmostEqual(pred.risk_probability, 0.65)
        self.assertFalse(pred.is_demo)

    def test_prediction_str(self):
        pred = WaterPrediction.objects.create(
            region=self.region,
            horizon_days=14,
            risk_probability=0.3,
            risk_level='LOW',
            predicted_reservoir_level=70.0,
            predicted_consumption=150.0,
        )
        s = str(pred)
        self.assertIn('Pred Model Region', s)
        self.assertIn('LOW', s)
        self.assertIn('14', s)

    def test_risk_color_property(self):
        pred = WaterPrediction(risk_level='MODERATE')
        self.assertEqual(pred.risk_color, 'warning')


class PredictionViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='preduser', password='pass123')
        self.region = make_region('View Pred Region')

    def test_list_requires_login(self):
        response = self.client.get(reverse('predictions:list'))
        self.assertEqual(response.status_code, 302)

    def test_list_accessible(self):
        self.client.login(username='preduser', password='pass123')
        response = self.client.get(reverse('predictions:list'))
        self.assertEqual(response.status_code, 200)
