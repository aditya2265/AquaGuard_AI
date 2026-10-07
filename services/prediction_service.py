"""
Prediction service: computes risk scores and generates WaterPrediction + RiskAssessment
objects from the latest available measurements.
"""
from datetime import date, timedelta
from apps.regions.models import Region
from apps.water_data.models import WaterMeasurement, WeatherMeasurement
from apps.predictions.models import WaterPrediction, RiskAssessment


RISK_THRESHOLDS = {
    'LOW': 0.25,
    'MODERATE': 0.50,
    'HIGH': 0.75,
    'CRITICAL': 1.01,
}


def risk_level_from_probability(prob: float) -> str:
    for level, threshold in RISK_THRESHOLDS.items():
        if prob < threshold:
            return level
    return 'CRITICAL'


def compute_risk_factors(measurements, weather_measurements):
    """
    Derive individual risk factor scores (0-1) from recent measurements.
    Returns a dict of factor_name -> score.
    """
    if not measurements:
        return {
            'reservoir_factor': 0.5,
            'rainfall_factor': 0.5,
            'consumption_factor': 0.5,
            'temperature_factor': 0.3,
            'demand_factor': 0.4,
        }

    recent = measurements[:30]
    latest = recent[0]

    # Reservoir factor: inverse of fill level
    reservoir_factor = max(0.0, min(1.0, (100 - latest.reservoir_level) / 100))

    # Rainfall factor: low rainfall = higher risk
    avg_rainfall = sum(m.rainfall_mm for m in recent) / len(recent)
    rainfall_factor = max(0.0, min(1.0, 1.0 - (avg_rainfall / 20.0)))

    # Consumption factor: relative to a baseline
    avg_consumption = sum(m.water_consumption_mld for m in recent) / len(recent)
    consumption_factor = min(1.0, avg_consumption / 500.0)

    # Temperature factor
    if weather_measurements:
        avg_temp = sum(w.temperature_celsius for w in weather_measurements[:30]) / len(weather_measurements[:30])
        temperature_factor = min(1.0, max(0.0, (avg_temp - 20) / 25))
    else:
        temperature_factor = 0.3

    # Demand factor (net outflow pressure)
    avg_net_flow = sum(m.inflow_mcm - m.outflow_mcm for m in recent) / len(recent)
    demand_factor = max(0.0, min(1.0, 0.5 - avg_net_flow / 2.0))

    return {
        'reservoir_factor': round(reservoir_factor, 4),
        'rainfall_factor': round(rainfall_factor, 4),
        'consumption_factor': round(consumption_factor, 4),
        'temperature_factor': round(temperature_factor, 4),
        'demand_factor': round(demand_factor, 4),
    }


def generate_explanation(region_name, risk_level, factors, predicted_reservoir):
    """Generate a human-readable explanation for the risk prediction."""
    lines = [
        f'Risk assessment for {region_name}: {risk_level} risk level.',
        '',
        'Key contributing factors:',
    ]

    sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
    for name, score in sorted_factors:
        label = name.replace('_', ' ').title()
        impact = 'High impact' if score > 0.6 else ('Moderate impact' if score > 0.35 else 'Low impact')
        lines.append(f'  • {label}: {score:.0%} — {impact}')

    lines += [
        '',
        f'Predicted reservoir level at end of horizon: {predicted_reservoir:.1f}%.',
    ]

    if risk_level == 'CRITICAL':
        lines.append('Immediate action required. Water shortage is highly likely.')
    elif risk_level == 'HIGH':
        lines.append('Proactive measures recommended to avoid shortage.')
    elif risk_level == 'MODERATE':
        lines.append('Monitor situation closely and prepare contingency measures.')
    else:
        lines.append('Situation is stable. Continue regular monitoring.')

    return '\n'.join(lines)


def run_prediction_for_region(region: Region, horizon_days: int = 7, is_demo: bool = False):
    """
    Run a prediction for a single region and horizon.
    Creates/updates WaterPrediction and RiskAssessment.
    Returns the WaterPrediction instance.
    """
    measurements = list(
        WaterMeasurement.objects.filter(region=region).order_by('-date')[:60]
    )
    weather = list(
        WeatherMeasurement.objects.filter(region=region).order_by('-date')[:30]
    )

    factors = compute_risk_factors(measurements, weather)

    # Weighted risk probability
    weights = {
        'reservoir_factor': 0.35,
        'rainfall_factor': 0.25,
        'consumption_factor': 0.20,
        'temperature_factor': 0.10,
        'demand_factor': 0.10,
    }
    risk_probability = sum(factors[k] * w for k, w in weights.items())
    risk_probability = round(min(1.0, max(0.0, risk_probability)), 4)
    risk_level = risk_level_from_probability(risk_probability)
    risk_score = round(risk_probability * 100, 2)

    # Predict future reservoir level (simple linear extrapolation)
    if measurements and len(measurements) >= 7:
        recent_7 = measurements[:7]
        avg_delta = (recent_7[-1].reservoir_level - recent_7[0].reservoir_level) / 7
        predicted_reservoir = max(0, min(100, measurements[0].reservoir_level + avg_delta * horizon_days))
    elif measurements:
        predicted_reservoir = measurements[0].reservoir_level
    else:
        predicted_reservoir = 50.0

    predicted_consumption = (
        sum(m.water_consumption_mld for m in measurements[:7]) / min(7, len(measurements))
        if measurements else 250.0
    )

    # Expected shortage start
    expected_shortage_start = None
    if risk_level in ('HIGH', 'CRITICAL') and measurements:
        days_to_shortage = max(1, int((measurements[0].reservoir_level / 100) * 30))
        expected_shortage_start = date.today() + timedelta(days=days_to_shortage)

    prediction = WaterPrediction.objects.create(
        region=region,
        horizon_days=horizon_days,
        risk_probability=risk_probability,
        risk_level=risk_level,
        predicted_reservoir_level=round(predicted_reservoir, 2),
        predicted_consumption=round(predicted_consumption, 2),
        expected_shortage_start=expected_shortage_start,
        model_version='1.0.0',
        is_demo=is_demo,
    )

    explanation = generate_explanation(region.name, risk_level, factors, predicted_reservoir)
    contributing = {k: round(v * weights[k] / risk_probability * 100, 1) if risk_probability > 0 else 0
                    for k, v in factors.items()}

    RiskAssessment.objects.create(
        prediction=prediction,
        risk_score=risk_score,
        rainfall_factor=factors['rainfall_factor'],
        reservoir_factor=factors['reservoir_factor'],
        consumption_factor=factors['consumption_factor'],
        temperature_factor=factors['temperature_factor'],
        demand_factor=factors['demand_factor'],
        contributing_factors=contributing,
        explanation_text=explanation,
    )

    return prediction
