"""
Rule-based risk scoring engine for AquaGuard.
Used as a fallback when ML models are not available,
and as the ground-truth factor calculator in all paths.
"""

RISK_WEIGHTS = {
    'reservoir': 0.35,
    'rainfall': 0.25,
    'consumption': 0.20,
    'temperature': 0.10,
    'demand': 0.10,
}

RISK_THRESHOLDS = {
    'LOW':      (0,  25),
    'MODERATE': (26, 50),
    'HIGH':     (51, 75),
    'CRITICAL': (76, 100),
}

RISK_COLORS = {
    'LOW':      '#22c55e',
    'MODERATE': '#f59e0b',
    'HIGH':     '#f97316',
    'CRITICAL': '#ef4444',
}


def calculate_risk_score(
    reservoir_level: float,
    rainfall_mm: float,
    rainfall_avg: float,
    consumption_mld: float,
    consumption_avg: float,
    temperature: float,
    temperature_avg: float,
    groundwater_level: float = 50.0,
) -> dict:
    """
    Compute a composite risk score and return a full result dict.

    Returns:
        {
            'score': float (0-100),
            'level': str,
            'probability': float (0-1),
            'factors': {
                'reservoir': float,
                'rainfall': float,
                'consumption': float,
                'temperature': float,
                'demand': float,
            }
        }
    """
    # Reservoir component: empty = high risk
    reservoir_factor = float(max(0.0, min(100.0, 100.0 - reservoir_level)))

    # Rainfall component: deviation below average
    if rainfall_avg > 0:
        rain_ratio = (rainfall_avg - rainfall_mm) / rainfall_avg * 100
        rainfall_factor = float(max(0.0, min(100.0, 50.0 + rain_ratio)))
    else:
        rainfall_factor = 50.0

    # Consumption component: how much above average
    if consumption_avg > 0:
        cons_ratio = (consumption_mld - consumption_avg) / consumption_avg * 100
        consumption_factor = float(max(0.0, min(100.0, 50.0 + cons_ratio)))
    else:
        consumption_factor = 50.0

    # Temperature component: deviation from average
    temp_diff = temperature - temperature_avg
    temperature_factor = float(max(0.0, min(100.0, 50.0 + temp_diff * 5.0)))

    # Demand component: re-use consumption deviation as proxy
    demand_factor = consumption_factor

    score = (
        RISK_WEIGHTS['reservoir']   * reservoir_factor
        + RISK_WEIGHTS['rainfall']    * rainfall_factor
        + RISK_WEIGHTS['consumption'] * consumption_factor
        + RISK_WEIGHTS['temperature'] * temperature_factor
        + RISK_WEIGHTS['demand']      * demand_factor
    )
    score = max(0.0, min(100.0, score))

    factors = {
        'reservoir':   round(reservoir_factor, 2),
        'rainfall':    round(rainfall_factor, 2),
        'consumption': round(consumption_factor, 2),
        'temperature': round(temperature_factor, 2),
        'demand':      round(demand_factor, 2),
    }

    return {
        'score':       round(score, 2),
        'level':       get_risk_level(score),
        'probability': round(score / 100.0, 4),
        'factors':     factors,
    }


def get_risk_level(score: float) -> str:
    """Map a 0-100 score to LOW / MODERATE / HIGH / CRITICAL."""
    if score <= 25:
        return 'LOW'
    elif score <= 50:
        return 'MODERATE'
    elif score <= 75:
        return 'HIGH'
    else:
        return 'CRITICAL'


def generate_explanation(factors: dict, risk_level: str) -> str:
    """
    Generate a human-readable explanation based on factor values.
    No LLM — purely rule-based.
    """
    lines = [f"Water shortage risk is {risk_level}"]

    dominant = max(factors, key=lambda k: factors[k])
    dominant_val = factors[dominant]

    factor_labels = {
        'reservoir':   'reservoir level',
        'rainfall':    'rainfall deficit',
        'consumption': 'water consumption',
        'temperature': 'temperature anomaly',
        'demand':      'demand growth',
    }

    lines[0] += f" primarily because of elevated {factor_labels.get(dominant, dominant)}."

    details = []
    if factors.get('reservoir', 0) > 60:
        details.append("Reservoir levels are critically low, reducing available water storage.")
    elif factors.get('reservoir', 0) > 40:
        details.append("Reservoir levels are below normal, limiting buffer capacity.")

    if factors.get('rainfall', 0) > 65:
        details.append("Rainfall is significantly below the historical average.")
    elif factors.get('rainfall', 0) > 50:
        details.append("Rainfall is slightly below normal.")

    if factors.get('consumption', 0) > 65:
        details.append("Water consumption is running above typical levels.")

    if factors.get('temperature', 0) > 65:
        details.append("Above-average temperatures are increasing evaporation and demand.")

    if factors.get('demand', 0) > 65:
        details.append("Long-term demand growth is putting pressure on supply.")

    if not details:
        details.append("All indicators are within acceptable ranges.")

    if risk_level == 'CRITICAL':
        details.append("Immediate intervention is recommended to prevent a supply crisis.")
    elif risk_level == 'HIGH':
        details.append("Proactive conservation measures should be implemented.")
    elif risk_level == 'MODERATE':
        details.append("Monitoring should be increased and early measures considered.")

    return " ".join(lines + details)


def get_risk_color(risk_level: str) -> str:
    """Return the hex colour for a given risk level."""
    return RISK_COLORS.get(risk_level, '#6b7280')
