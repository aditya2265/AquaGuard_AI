from django.test import TestCase
from ml.risk_engine import (
    calculate_risk_score,
    get_risk_level,
    get_risk_color,
    generate_explanation,
    RISK_WEIGHTS,
    RISK_THRESHOLDS,
)


class RiskEngineUnitTest(TestCase):

    def _calc(self, reservoir=50.0, rainfall=5.0, rainfall_avg=5.0,
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

    def test_calculate_risk_score_returns_dict(self):
        result = self._calc()
        self.assertIsInstance(result, dict)
        for key in ('score', 'level', 'probability', 'factors'):
            self.assertIn(key, result)

    def test_risk_score_clipped_0_100(self):
        # Extreme low risk
        result_low = self._calc(reservoir=100.0, rainfall=50.0, rainfall_avg=1.0)
        self.assertGreaterEqual(result_low['score'], 0.0)
        self.assertLessEqual(result_low['score'], 100.0)

        # Extreme high risk
        result_high = self._calc(reservoir=0.0, rainfall=0.0, rainfall_avg=50.0,
                                  consumption=500.0, consumption_avg=100.0,
                                  temperature=50.0, temperature_avg=25.0)
        self.assertGreaterEqual(result_high['score'], 0.0)
        self.assertLessEqual(result_high['score'], 100.0)

    def test_get_risk_level(self):
        self.assertEqual(get_risk_level(0),   'LOW')
        self.assertEqual(get_risk_level(25),  'LOW')
        self.assertEqual(get_risk_level(26),  'MODERATE')
        self.assertEqual(get_risk_level(50),  'MODERATE')
        self.assertEqual(get_risk_level(51),  'HIGH')
        self.assertEqual(get_risk_level(75),  'HIGH')
        self.assertEqual(get_risk_level(76),  'CRITICAL')
        self.assertEqual(get_risk_level(100), 'CRITICAL')

    def test_get_risk_color(self):
        self.assertEqual(get_risk_color('LOW'),      '#22c55e')
        self.assertEqual(get_risk_color('MODERATE'), '#f59e0b')
        self.assertEqual(get_risk_color('HIGH'),     '#f97316')
        self.assertEqual(get_risk_color('CRITICAL'), '#ef4444')

    def test_explanation_not_empty(self):
        result = self._calc(reservoir=30.0, rainfall=1.0, rainfall_avg=10.0)
        explanation = generate_explanation(result['factors'], result['level'])
        self.assertIsInstance(explanation, str)
        self.assertGreater(len(explanation), 20)

    def test_factors_all_present(self):
        result = self._calc()
        factors = result['factors']
        for key in ('reservoir', 'rainfall', 'consumption', 'temperature', 'demand'):
            self.assertIn(key, factors)

    def test_factors_clipped_to_range(self):
        result = self._calc(reservoir=0.0, rainfall=0.0, rainfall_avg=100.0)
        for key, val in result['factors'].items():
            self.assertGreaterEqual(val, 0.0, f'Factor {key} below 0')
            self.assertLessEqual(val, 100.0, f'Factor {key} above 100')

    def test_probability_is_score_divided_100(self):
        result = self._calc(reservoir=40.0, rainfall=3.0, rainfall_avg=8.0)
        self.assertAlmostEqual(result['probability'], result['score'] / 100.0, places=3)

    def test_high_reservoir_reduces_risk(self):
        high = self._calc(reservoir=90.0)
        low = self._calc(reservoir=10.0)
        self.assertLess(high['score'], low['score'])

    def test_zero_rainfall_avg_no_crash(self):
        """When rainfall_avg=0, the function should return a stable result."""
        result = calculate_risk_score(
            reservoir_level=50.0,
            rainfall_mm=5.0,
            rainfall_avg=0.0,
            consumption_mld=100.0,
            consumption_avg=100.0,
            temperature=25.0,
            temperature_avg=25.0,
        )
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)


class RecommendationServiceTest(TestCase):

    def _get_recommendations(self, risk_level, reservoir=50.0):
        """Use the LocalAIProvider to generate recommendations."""
        from services.ai_provider import LocalAIProvider
        from ml.risk_engine import calculate_risk_score

        result = calculate_risk_score(
            reservoir_level=reservoir,
            rainfall_mm=2.0,
            rainfall_avg=10.0,
            consumption_mld=150.0,
            consumption_avg=100.0,
            temperature=30.0,
            temperature_avg=25.0,
        )
        provider = LocalAIProvider()
        return provider.generate_recommendations(result['factors'], risk_level, 'Test Region')

    def test_recommendations_generated_for_high_risk(self):
        recs = self._get_recommendations('HIGH', reservoir=20.0)
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)

    def test_recommendations_generated_for_low_risk(self):
        recs = self._get_recommendations('LOW', reservoir=80.0)
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)

    def test_recommendations_not_empty(self):
        recs = self._get_recommendations('MODERATE')
        for rec in recs:
            self.assertIn('title', rec)
            self.assertIn('description', rec)
            self.assertGreater(len(rec['title']), 0)

    def test_explanation_generation(self):
        from services.ai_provider import LocalAIProvider
        provider = LocalAIProvider()
        factors = {
            'reservoir': 80.0,
            'rainfall': 70.0,
            'consumption': 60.0,
            'temperature': 55.0,
            'demand': 60.0,
        }
        explanation = provider.generate_explanation(factors, 'HIGH')
        self.assertIsInstance(explanation, str)
        self.assertGreater(len(explanation), 10)
