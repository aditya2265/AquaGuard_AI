"""
PredictionService: generates water shortage risk predictions for regions.
Tries to use trained ML models; falls back to the rule-based risk engine.
"""
import logging
from pathlib import Path
from datetime import date, timedelta

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent / 'models'
CLASSIFIER_PATH = MODELS_DIR / 'risk_classifier.joblib'
REGRESSOR_PATH = MODELS_DIR / 'shortage_regressor.joblib'


class PredictionService:
    _classifier = None
    _regressor = None
    _models_loaded = False

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    @classmethod
    def load_models(cls):
        """Load joblib models from disk. Falls back gracefully if absent."""
        try:
            import joblib
            if CLASSIFIER_PATH.exists():
                cls._classifier = joblib.load(CLASSIFIER_PATH)
                logger.info("Risk classifier loaded from %s", CLASSIFIER_PATH)
            else:
                logger.warning("Risk classifier not found at %s — using fallback.", CLASSIFIER_PATH)

            if REGRESSOR_PATH.exists():
                cls._regressor = joblib.load(REGRESSOR_PATH)
                logger.info("Shortage regressor loaded from %s", REGRESSOR_PATH)
            else:
                logger.warning("Shortage regressor not found at %s — using fallback.", REGRESSOR_PATH)
        except Exception as exc:
            logger.error("Failed to load ML models: %s — using fallback.", exc)
            cls._classifier = None
            cls._regressor = None
        finally:
            cls._models_loaded = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _load_region_data(cls, region_id: int, days: int = 90):
        """Return a preprocessed, feature-engineered DataFrame for a region."""
        from ml.preprocessing import WaterDataPreprocessor
        from ml.features import engineer_features

        preprocessor = WaterDataPreprocessor()
        raw = preprocessor.load_from_db(region_id=region_id, days=days)
        if raw.empty:
            return raw
        df = preprocessor.clean(raw)
        df = preprocessor.encode(df)
        df = engineer_features(df)
        return df

    @classmethod
    def _ml_predict(cls, df):
        """
        Use ML models if loaded; return (risk_level, risk_probability).
        Returns None if models are unavailable.
        """
        from ml.features import FEATURE_COLUMNS
        present_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
        valid = df.dropna(subset=present_cols)
        if valid.empty:
            return None

        X = valid[present_cols].tail(1).values
        try:
            risk_level = cls._classifier.predict(X)[0] if cls._classifier else None
            risk_prob = float(cls._regressor.predict(X)[0].clip(0, 1)) if cls._regressor else None
            if risk_level and risk_prob is not None:
                return risk_level, risk_prob
        except Exception as exc:
            logger.warning("ML prediction failed: %s", exc)
        return None

    @classmethod
    def _fallback_predict(cls, df):
        """
        Compute risk via rule-based engine using the most recent row.
        Returns (risk_level, risk_probability, risk_result_dict).
        """
        from ml.risk_engine import calculate_risk_score

        if df.empty:
            result = calculate_risk_score(50, 5, 10, 100, 100, 25, 25)
            return result['level'], result['probability'], result

        last = df.iloc[-1]
        # Historical averages from the same dataset
        rainfall_avg = df['rainfall_mm'].mean() if 'rainfall_mm' in df else 10.0
        consumption_avg = df['water_consumption_mld'].mean() if 'water_consumption_mld' in df else last.get('water_consumption_mld', 100)
        temperature_avg = df['temperature_celsius'].mean() if 'temperature_celsius' in df else last.get('temperature_celsius', 25)

        result = calculate_risk_score(
            reservoir_level=float(last.get('reservoir_level', 50)),
            rainfall_mm=float(last.get('rainfall_mm', 5)),
            rainfall_avg=float(rainfall_avg),
            consumption_mld=float(last.get('water_consumption_mld', 100)),
            consumption_avg=float(consumption_avg),
            temperature=float(last.get('temperature_celsius', 25)),
            temperature_avg=float(temperature_avg),
            groundwater_level=float(last.get('groundwater_level_m', 50)),
        )
        return result['level'], result['probability'], result

    @classmethod
    def _build_contributing_factors(cls, df, risk_result: dict) -> dict:
        """Merge ML-derived factors with most recent measurements."""
        factors = dict(risk_result.get('factors', {}))
        if not df.empty:
            last = df.iloc[-1]
            factors['reservoir_level'] = round(float(last.get('reservoir_level', 50)), 2)
            factors['rainfall_mm'] = round(float(last.get('rainfall_mm', 0)), 2)
            factors['rainfall_deviation'] = round(float(last.get('rainfall_deviation', 0)), 4)
            factors['consumption_growth'] = round(float(last.get('consumption_growth', 0)), 4)
            factors['temp_anomaly'] = round(float(last.get('temp_anomaly', 0)), 4)
        return factors

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def predict_region(cls, region_id: int, horizon_days: int = 30) -> dict:
        """
        Generate a prediction for a single region and horizon.
        Saves WaterPrediction + RiskAssessment to DB.
        Returns the prediction as a dict.
        """
        from apps.regions.models import Region
        from apps.predictions.models import WaterPrediction, RiskAssessment
        from ml.risk_engine import generate_explanation, get_risk_color

        if not cls._models_loaded:
            cls.load_models()

        try:
            region = Region.objects.get(pk=region_id)
        except Region.DoesNotExist:
            raise ValueError(f"Region {region_id} does not exist.")

        df = cls._load_region_data(region_id, days=90)

        # Try ML path first
        ml_result = None if df.empty else cls._ml_predict(df)

        if ml_result:
            risk_level, risk_probability = ml_result
            _, _, risk_result = cls._fallback_predict(df)   # still need factor dict
            risk_result['level'] = risk_level
            risk_result['probability'] = risk_probability
            risk_result['score'] = round(risk_probability * 100, 2)
        else:
            risk_level, risk_probability, risk_result = cls._fallback_predict(df)

        # Horizon scaling: longer horizon → slightly elevated risk
        horizon_factor = 1.0 + (horizon_days - 7) * 0.002
        adjusted_prob = min(1.0, risk_probability * horizon_factor)

        contributing_factors = cls._build_contributing_factors(df, risk_result)
        explanation = generate_explanation(contributing_factors, risk_level)

        # Latest reservoir / consumption for prediction record
        last_reservoir = 50.0
        last_consumption = 100.0
        if not df.empty:
            last = df.iloc[-1]
            last_reservoir = float(last.get('reservoir_level', 50))
            last_consumption = float(last.get('water_consumption_mld', 100))

        # Save prediction
        prediction = WaterPrediction.objects.create(
            region=region,
            horizon_days=horizon_days,
            risk_probability=round(adjusted_prob, 4),
            risk_level=risk_level,
            predicted_reservoir_level=round(max(0, last_reservoir - horizon_days * 0.1), 2),
            predicted_consumption=round(last_consumption * (1 + 0.001 * horizon_days), 2),
            model_version='1.0.0',
        )

        # Save risk assessment
        RiskAssessment.objects.create(
            prediction=prediction,
            risk_score=round(risk_result['score'], 2),
            rainfall_factor=contributing_factors.get('rainfall', 0),
            reservoir_factor=contributing_factors.get('reservoir', 0),
            consumption_factor=contributing_factors.get('consumption', 0),
            temperature_factor=contributing_factors.get('temperature', 0),
            demand_factor=contributing_factors.get('demand', 0),
            contributing_factors=contributing_factors,
            explanation_text=explanation,
        )

        return {
            'region_id': region_id,
            'region_name': region.name,
            'horizon_days': horizon_days,
            'risk_level': risk_level,
            'risk_probability': round(adjusted_prob, 4),
            'risk_score': round(risk_result['score'], 2),
            'risk_color': get_risk_color(risk_level),
            'contributing_factors': contributing_factors,
            'explanation': explanation,
            'prediction_id': prediction.pk,
        }

    @classmethod
    def predict_multi_horizon(cls, region_id: int) -> list:
        """Return predictions for 7, 14, and 30-day horizons."""
        results = []
        for horizon in (7, 14, 30):
            try:
                result = cls.predict_region(region_id, horizon_days=horizon)
                results.append(result)
            except Exception as exc:
                logger.error("Prediction failed for region %s, horizon %d: %s", region_id, horizon, exc)
        return results

    @classmethod
    def batch_predict_all_regions(cls):
        """Run predict_region for every active region."""
        from apps.regions.models import Region

        regions = Region.objects.filter(is_active=True)
        results = []
        for region in regions:
            try:
                result = cls.predict_region(region.pk, horizon_days=30)
                results.append(result)
                logger.info("Predicted for region %s: %s", region.name, result['risk_level'])
            except Exception as exc:
                logger.error("Batch prediction failed for region %s: %s", region.name, exc)
        return results
