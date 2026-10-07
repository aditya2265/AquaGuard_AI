"""
Rule-based recommendation and alert generation for AquaGuard.
"""
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Rule definitions
# ------------------------------------------------------------------
# Each rule is a dict:
#   condition_fn(factors) -> bool
#   priority, category, title, description, action_required

RECOMMENDATION_RULES = [
    {
        'condition_fn': lambda f: f.get('rainfall_deviation', 0) < -0.20,
        'priority': 'HIGH',
        'category': 'conservation',
        'title': 'Activate Water Conservation Measures',
        'description': (
            'Rainfall is significantly below average. Implement immediate water '
            'conservation protocols to reduce demand pressure on existing supplies.'
        ),
        'action_required': (
            'Issue public advisory to reduce non-essential water use. '
            'Activate tiered pricing for high-consumption households. '
            'Review and restrict commercial/industrial usage permits.'
        ),
    },
    {
        'condition_fn': lambda f: f.get('rainfall_deviation', 0) < -0.20,
        'priority': 'MEDIUM',
        'category': 'planning',
        'title': 'Deploy Rainwater Harvesting Infrastructure',
        'description': (
            'Below-average rainfall trend suggests structural dependency on stored water. '
            'Expand rainwater harvesting capacity to build resilience.'
        ),
        'action_required': (
            'Audit existing rainwater harvesting systems for maintenance. '
            'Identify sites for new collection infrastructure. '
            'Provide incentives for household-level rainwater capture.'
        ),
    },
    {
        'condition_fn': lambda f: 20 < f.get('reservoir_level', 100) <= 40,
        'priority': 'HIGH',
        'category': 'supply',
        'title': 'Activate Supply Planning Protocol',
        'description': (
            'Reservoir level has dropped below 40%. Supply planning and demand '
            'management must be activated to prevent critical shortfalls.'
        ),
        'action_required': (
            'Initiate emergency water procurement from alternative sources. '
            'Implement scheduled supply rotations by zone. '
            'Alert downstream treatment facilities of reduced inflows.'
        ),
    },
    {
        'condition_fn': lambda f: f.get('reservoir_level', 100) <= 20,
        'priority': 'CRITICAL',
        'category': 'supply',
        'title': 'Emergency Reservoir Management Required',
        'description': (
            'Reservoir level is critically low (≤20%). Immediate emergency '
            'measures are required to prevent a total supply failure.'
        ),
        'action_required': (
            'Declare water emergency and activate contingency supply plan. '
            'Prioritise water for drinking, sanitation, and essential services. '
            'Coordinate with state authorities for emergency water tanker deployment.'
        ),
    },
    {
        'condition_fn': lambda f: f.get('consumption_growth', 0) > 0.15,
        'priority': 'HIGH',
        'category': 'conservation',
        'title': 'Demand Management Intervention',
        'description': (
            'Water consumption has grown more than 15% above baseline. '
            'Structural demand management is required to prevent supply shortfalls.'
        ),
        'action_required': (
            'Conduct rapid demand audit across residential, commercial, and industrial sectors. '
            'Issue mandatory usage restrictions for non-essential applications. '
            'Deploy smart meters to identify abnormal consumption patterns.'
        ),
    },
    {
        'condition_fn': lambda f: f.get('temp_anomaly', 0) > 2.0,
        'priority': 'MEDIUM',
        'category': 'monitoring',
        'title': 'Review Irrigation and Evaporation Losses',
        'description': (
            'Above-average temperatures are increasing evapotranspiration rates, '
            'accelerating reservoir evaporation and agricultural water demand.'
        ),
        'action_required': (
            'Audit open-channel irrigation for conversion to drip/sprinkler systems. '
            'Install evaporation monitoring at key reservoirs. '
            'Coordinate with agriculture department to align crop calendars with water availability.'
        ),
    },
    {
        'condition_fn': lambda f, rl='': rl == 'CRITICAL',
        'priority': 'CRITICAL',
        'category': 'planning',
        'title': 'Activate Public Awareness Campaign',
        'description': (
            'Risk level has reached CRITICAL. Public communication is essential '
            'to ensure community cooperation with emergency water management.'
        ),
        'action_required': (
            'Launch multi-channel public awareness campaign (radio, SMS, social media). '
            'Publish daily water status bulletins. '
            'Activate community water wardens for neighbourhood-level compliance.'
        ),
    },
    {
        'condition_fn': lambda f, rl='': rl in ('HIGH', 'CRITICAL'),
        'priority': 'HIGH',
        'category': 'planning',
        'title': 'Develop Contingency Supply Plan',
        'description': (
            'Elevated risk level requires a documented contingency supply plan '
            'to ensure continuity of essential water services.'
        ),
        'action_required': (
            'Review and update emergency water supply protocols. '
            'Establish agreements with neighbouring utilities for inter-basin transfers. '
            'Pre-position mobile water treatment units in vulnerable zones.'
        ),
    },
]

# Baseline recommendations always generated regardless of risk
_BASELINE_RECOMMENDATIONS = [
    {
        'priority': 'LOW',
        'category': 'monitoring',
        'title': 'Maintain Routine Water Quality Monitoring',
        'description': (
            'Regular water quality monitoring is essential to detect contamination '
            'risks early and ensure compliance with safety standards.'
        ),
        'action_required': (
            'Conduct weekly water quality tests at treatment plants and distribution points. '
            'Maintain testing logs and share results with public health authorities.'
        ),
    },
    {
        'priority': 'LOW',
        'category': 'conservation',
        'title': 'Continue Public Water Conservation Education',
        'description': (
            'Ongoing public education sustains water-saving behaviours and '
            'builds long-term community resilience to supply variability.'
        ),
        'action_required': (
            'Run seasonal awareness campaigns in schools and community centres. '
            'Distribute water-saving tips through utility bill inserts and social media.'
        ),
    },
]


# ------------------------------------------------------------------
# Public functions
# ------------------------------------------------------------------

def generate_recommendations(factors: dict, risk_level: str, region_name: str) -> list:
    """
    Apply RECOMMENDATION_RULES to produce a prioritised recommendation list.
    Always returns at least 2 recommendations.
    """
    results = []
    seen_titles = set()

    for rule in RECOMMENDATION_RULES:
        try:
            cond = rule['condition_fn']
            # Rules that also check risk_level accept a second argument
            import inspect
            sig = inspect.signature(cond)
            if len(sig.parameters) == 2:
                triggered = cond(factors, risk_level)
            else:
                triggered = cond(factors)
        except Exception:
            triggered = False

        if triggered and rule['title'] not in seen_titles:
            seen_titles.add(rule['title'])
            results.append({
                'priority': rule['priority'],
                'category': rule['category'],
                'title': rule['title'],
                'description': rule['description'],
                'action_required': rule['action_required'],
            })

    # Pad with baseline recommendations to reach a minimum of 2
    for baseline in _BASELINE_RECOMMENDATIONS:
        if len(results) >= 2:
            break
        if baseline['title'] not in seen_titles:
            results.append(baseline)
            seen_titles.add(baseline['title'])

    return results


def save_recommendations(region_id: int, prediction_id, recommendations: list):
    """
    Persist Recommendation objects to DB.
    Skips duplicates active in the last 7 days (same region + title).
    """
    from django.utils import timezone
    from apps.recommendations.models import Recommendation
    from apps.predictions.models import WaterPrediction

    cutoff = timezone.now() - timedelta(days=7)
    recent_titles = set(
        Recommendation.objects.filter(
            region_id=region_id,
            is_active=True,
            created_at__gte=cutoff,
        ).values_list('title', flat=True)
    )

    prediction = None
    if prediction_id:
        try:
            prediction = WaterPrediction.objects.get(pk=prediction_id)
        except WaterPrediction.DoesNotExist:
            pass

    created = 0
    for rec in recommendations:
        if rec.get('title') in recent_titles:
            continue
        Recommendation.objects.create(
            region_id=region_id,
            prediction=prediction,
            priority=rec.get('priority', 'MEDIUM'),
            category=rec.get('category', 'conservation'),
            title=rec['title'],
            description=rec.get('description', ''),
            action_required=rec.get('action_required', ''),
        )
        created += 1

    logger.info("Saved %d new recommendations for region_id=%s", created, region_id)
    return created


def generate_alerts(region_id: int, prediction_result: dict):
    """
    Create Alert objects based on the prediction result.
    Deduplicates by alert_type + region within 24 hours.
    """
    from django.utils import timezone
    from apps.alerts.models import Alert

    risk_level = prediction_result.get('risk_level', 'LOW')
    factors = prediction_result.get('contributing_factors', {})
    cutoff = timezone.now() - timedelta(hours=24)

    def _recent(alert_type: str) -> bool:
        return Alert.objects.filter(
            region_id=region_id,
            alert_type=alert_type,
            created_at__gte=cutoff,
        ).exists()

    alerts_to_create = []

    # Reservoir level alert
    reservoir = factors.get('reservoir_level', 100)
    if reservoir <= 20 and not _recent('reservoir'):
        alerts_to_create.append(Alert(
            region_id=region_id,
            severity='CRITICAL',
            alert_type='reservoir',
            title='Critical Reservoir Level',
            message=f'Reservoir level has dropped to {reservoir:.1f}%. Immediate action required.',
        ))
    elif reservoir <= 40 and not _recent('reservoir'):
        alerts_to_create.append(Alert(
            region_id=region_id,
            severity='HIGH',
            alert_type='reservoir',
            title='Low Reservoir Level',
            message=f'Reservoir level at {reservoir:.1f}%. Supply planning protocols should be activated.',
        ))

    # Rainfall alert
    rain_dev = factors.get('rainfall_deviation', 0)
    if rain_dev < -0.30 and not _recent('rainfall'):
        alerts_to_create.append(Alert(
            region_id=region_id,
            severity='WARNING',
            alert_type='rainfall',
            title='Significant Rainfall Deficit',
            message=f'Rainfall is {abs(rain_dev)*100:.0f}% below the seasonal average.',
        ))

    # Overall prediction alert
    if risk_level == 'CRITICAL' and not _recent('prediction'):
        alerts_to_create.append(Alert(
            region_id=region_id,
            severity='CRITICAL',
            alert_type='prediction',
            title='Critical Water Shortage Risk',
            message=(
                f'AI prediction indicates CRITICAL water shortage risk. '
                f'Score: {prediction_result.get("risk_score", 0):.1f}/100.'
            ),
        ))
    elif risk_level == 'HIGH' and not _recent('prediction'):
        alerts_to_create.append(Alert(
            region_id=region_id,
            severity='HIGH',
            alert_type='prediction',
            title='High Water Shortage Risk',
            message=(
                f'AI prediction indicates HIGH water shortage risk. '
                f'Score: {prediction_result.get("risk_score", 0):.1f}/100.'
            ),
        ))

    if alerts_to_create:
        Alert.objects.bulk_create(alerts_to_create)
        logger.info("Created %d alerts for region_id=%s", len(alerts_to_create), region_id)

    return alerts_to_create
