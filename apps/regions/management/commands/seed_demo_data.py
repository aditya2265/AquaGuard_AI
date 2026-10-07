"""
Management command: seed_demo_data

Creates realistic demo data for 8 Gujarat regions covering 180 days of
water and weather measurements, predictions, risk assessments,
recommendations, and alerts.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --reset
"""
import random
from datetime import date, timedelta, datetime
import numpy as np
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.regions.models import Region
from apps.water_data.models import WaterMeasurement, WeatherMeasurement
from apps.predictions.models import WaterPrediction, RiskAssessment
from apps.recommendations.models import Recommendation
from apps.alerts.models import Alert


# ---------------------------------------------------------------------------
# Region seed definitions
# ---------------------------------------------------------------------------
GUJARAT_REGIONS = [
    {
        'name': 'Rajkot',
        'state': 'Gujarat',
        'latitude': 22.3039,
        'longitude': 70.8022,
        'population': 1800000,
        'area_sq_km': 1040.0,
        'profile': 'high_risk',   # declining reservoir, low rainfall, high consumption
    },
    {
        'name': 'Jamnagar',
        'state': 'Gujarat',
        'latitude': 22.4707,
        'longitude': 70.0577,
        'population': 700000,
        'area_sq_km': 1475.0,
        'profile': 'moderate_risk',
    },
    {
        'name': 'Bhavnagar',
        'state': 'Gujarat',
        'latitude': 21.7645,
        'longitude': 72.1519,
        'population': 850000,
        'area_sq_km': 1082.0,
        'profile': 'low_risk',    # good monsoon coverage
    },
    {
        'name': 'Amreli',
        'state': 'Gujarat',
        'latitude': 21.6030,
        'longitude': 71.2214,
        'population': 300000,
        'area_sq_km': 1073.0,
        'profile': 'high_risk',
    },
    {
        'name': 'Surendranagar',
        'state': 'Gujarat',
        'latitude': 22.7270,
        'longitude': 71.6440,
        'population': 450000,
        'area_sq_km': 1095.0,
        'profile': 'moderate_risk',
    },
    {
        'name': 'Gondal',
        'state': 'Gujarat',
        'latitude': 21.9600,
        'longitude': 70.7900,
        'population': 120000,
        'area_sq_km': 380.0,
        'profile': 'low_risk',
    },
    {
        'name': 'Morbi',
        'state': 'Gujarat',
        'latitude': 22.8200,
        'longitude': 70.8400,
        'population': 250000,
        'area_sq_km': 620.0,
        'profile': 'moderate_risk',
    },
    {
        'name': 'Dwarka',
        'state': 'Gujarat',
        'latitude': 22.2378,
        'longitude': 68.9674,
        'population': 45000,
        'area_sq_km': 290.0,
        'profile': 'low_risk',
    },
]

# ---------------------------------------------------------------------------
# Profile parameter tables
# ---------------------------------------------------------------------------
PROFILE_PARAMS = {
    'high_risk': {
        'reservoir_start': 45.0,
        'reservoir_trend': -0.15,   # % per day overall
        'reservoir_capacity_mcm': 800.0,
        'base_consumption_mld': 310.0,
        'consumption_noise': 20.0,
        'groundwater_start': 19.0,
        'groundwater_trend': 0.03,  # rising (declining water table)
        'base_inflow': 0.8,
        'base_outflow': 1.3,
        'monsoon_rain_mean': 35.0,
        'dry_rain_mean': 0.5,
    },
    'moderate_risk': {
        'reservoir_start': 58.0,
        'reservoir_trend': -0.05,
        'reservoir_capacity_mcm': 600.0,
        'base_consumption_mld': 175.0,
        'consumption_noise': 15.0,
        'groundwater_start': 13.0,
        'groundwater_trend': 0.01,
        'base_inflow': 0.7,
        'base_outflow': 0.9,
        'monsoon_rain_mean': 50.0,
        'dry_rain_mean': 0.8,
    },
    'low_risk': {
        'reservoir_start': 72.0,
        'reservoir_trend': 0.02,
        'reservoir_capacity_mcm': 500.0,
        'base_consumption_mld': 120.0,
        'consumption_noise': 10.0,
        'groundwater_start': 9.5,
        'groundwater_trend': -0.005,
        'base_inflow': 2.0,
        'base_outflow': 1.4,
        'monsoon_rain_mean': 70.0,
        'dry_rain_mean': 1.5,
    },
}

HORIZON_DAYS = [7, 14, 30]

# Risk level definitions used for recommendation / alert generation
RISK_WEIGHTS = {
    'reservoir_factor': 0.35,
    'rainfall_factor': 0.25,
    'consumption_factor': 0.20,
    'temperature_factor': 0.10,
    'demand_factor': 0.10,
}


def _is_monsoon(day_of_year: int) -> bool:
    """Monsoon season: roughly day 180-270 (July–September)."""
    return 180 <= day_of_year <= 270


def _is_post_monsoon(day_of_year: int) -> bool:
    return 271 <= day_of_year <= 310


def _rainfall_for_day(day_of_year: int, params: dict, rng) -> float:
    if _is_monsoon(day_of_year):
        rain = rng.exponential(params['monsoon_rain_mean'])
        return min(float(rain), 200.0)
    elif _is_post_monsoon(day_of_year):
        rain = rng.exponential(params['dry_rain_mean'] * 3)
        return min(float(rain), 30.0)
    else:
        rain = rng.exponential(params['dry_rain_mean'])
        return min(float(rain), 10.0)


def _temperature_for_day(day_of_year: int, rng) -> float:
    # Summer peak ~42°C, winter ~18°C, sinusoidal
    baseline = 30.0 - 12.0 * np.cos(2 * np.pi * (day_of_year - 15) / 365)
    return float(baseline + rng.normal(0, 1.5))


def _humidity_for_day(day_of_year: int, rainfall_mm: float, rng) -> float:
    if _is_monsoon(day_of_year):
        base = 75.0 + rainfall_mm * 0.1
    else:
        base = 35.0 + rainfall_mm * 0.5
    return float(np.clip(base + rng.normal(0, 5), 15.0, 98.0))


def _generate_time_series(params: dict, days: int, start_date: date, rng):
    """
    Generate a list of dicts representing daily measurements for `days` days.
    """
    records = []
    reservoir_level = params['reservoir_start']
    groundwater = params['groundwater_start']
    capacity = params['reservoir_capacity_mcm']

    for i in range(days):
        current_date = start_date + timedelta(days=i)
        doy = current_date.timetuple().tm_yday

        rainfall = _rainfall_for_day(doy, params, rng)
        temperature = _temperature_for_day(doy, rng)
        humidity = _humidity_for_day(doy, rainfall, rng)
        wind_speed = float(np.clip(rng.normal(15.0, 5.0), 2.0, 60.0))

        # Reservoir dynamics
        if _is_monsoon(doy):
            inflow = float(max(0.1, rng.normal(params['base_inflow'] * 3, 0.5)))
        else:
            inflow = float(max(0.05, rng.normal(params['base_inflow'], 0.2)))
        outflow = float(max(0.1, rng.normal(params['base_outflow'], 0.15)))

        daily_rainfall_fill = (rainfall / 1000.0) * 50.0  # very rough conversion to % fill
        reservoir_delta = (inflow - outflow) * 0.05 + daily_rainfall_fill * 0.01 + params['reservoir_trend']
        reservoir_level = float(np.clip(reservoir_level + reservoir_delta + rng.normal(0, 0.3), 5.0, 100.0))
        current_storage = (reservoir_level / 100.0) * capacity

        # Groundwater
        if _is_monsoon(doy):
            groundwater = float(max(2.0, groundwater - 0.05 + rng.normal(0, 0.05)))
        else:
            groundwater = float(groundwater + params['groundwater_trend'] + rng.normal(0, 0.05))
        groundwater = float(np.clip(groundwater, 2.0, 40.0))

        consumption = float(max(10.0, rng.normal(params['base_consumption_mld'], params['consumption_noise'])))
        # Summer increases consumption
        if temperature > 35:
            consumption *= 1.15

        records.append({
            'date': current_date,
            'rainfall_mm': round(rainfall, 2),
            'temperature_celsius': round(temperature, 2),
            'humidity_percent': round(humidity, 2),
            'wind_speed_kmh': round(wind_speed, 2),
            'reservoir_level': round(reservoir_level, 2),
            'reservoir_capacity_mcm': capacity,
            'current_storage_mcm': round(current_storage, 2),
            'water_consumption_mld': round(consumption, 2),
            'groundwater_level_m': round(groundwater, 2),
            'inflow_mcm': round(inflow, 3),
            'outflow_mcm': round(outflow, 3),
        })

    return records


def _compute_factors(measurements: list) -> dict:
    if not measurements:
        return {k: 0.5 for k in ['reservoir_factor', 'rainfall_factor',
                                   'consumption_factor', 'temperature_factor', 'demand_factor']}
    latest = measurements[0]
    recent = measurements[:30]

    reservoir_factor = max(0.0, min(1.0, (100 - latest['reservoir_level']) / 100))
    avg_rainfall = sum(m['rainfall_mm'] for m in recent) / len(recent)
    rainfall_factor = max(0.0, min(1.0, 1.0 - (avg_rainfall / 20.0)))
    avg_consumption = sum(m['water_consumption_mld'] for m in recent) / len(recent)
    consumption_factor = min(1.0, avg_consumption / 500.0)
    avg_temp = sum(m['temperature_celsius'] for m in recent) / len(recent)
    temperature_factor = min(1.0, max(0.0, (avg_temp - 20) / 25))
    avg_net = sum(m['inflow_mcm'] - m['outflow_mcm'] for m in recent) / len(recent)
    demand_factor = max(0.0, min(1.0, 0.5 - avg_net / 2.0))

    return {
        'reservoir_factor': round(reservoir_factor, 4),
        'rainfall_factor': round(rainfall_factor, 4),
        'consumption_factor': round(consumption_factor, 4),
        'temperature_factor': round(temperature_factor, 4),
        'demand_factor': round(demand_factor, 4),
    }


def _risk_level_from_prob(prob: float) -> str:
    if prob < 0.25:
        return 'LOW'
    elif prob < 0.50:
        return 'MODERATE'
    elif prob < 0.75:
        return 'HIGH'
    return 'CRITICAL'


def _explanation(region_name, risk_level, factors, predicted_reservoir):
    lines = [
        f'Risk assessment for {region_name}: {risk_level} risk.',
        '',
        'Contributing factors:',
    ]
    for name, score in sorted(factors.items(), key=lambda x: x[1], reverse=True):
        label = name.replace('_', ' ').title()
        impact = 'High' if score > 0.6 else ('Moderate' if score > 0.35 else 'Low')
        lines.append(f'  • {label}: {score:.0%} — {impact} impact')
    lines += [
        '',
        f'Predicted reservoir level: {predicted_reservoir:.1f}%.',
    ]
    messages = {
        'CRITICAL': 'Immediate action required — shortage is imminent.',
        'HIGH': 'Proactive measures strongly recommended.',
        'MODERATE': 'Monitor closely and prepare contingency plans.',
        'LOW': 'Situation is stable. Continue routine monitoring.',
    }
    lines.append(messages.get(risk_level, ''))
    return '\n'.join(lines)


def _get_recommendations(region, prediction, risk_level, profile):
    recs = []

    if risk_level in ('HIGH', 'CRITICAL'):
        recs.append({
            'priority': 'CRITICAL' if risk_level == 'CRITICAL' else 'HIGH',
            'category': 'conservation',
            'title': f'Implement Emergency Water Conservation in {region.name}',
            'description': (
                f'{region.name} is facing {risk_level.lower()} water risk. '
                'Immediate conservation measures are essential to prevent shortage.'
            ),
            'action_required': (
                'Enforce odd-even water supply schedule. '
                'Restrict non-essential water usage. '
                'Deploy mobile water tankers to vulnerable areas. '
                'Issue public advisory for water conservation.'
            ),
        })
        recs.append({
            'priority': 'HIGH',
            'category': 'supply',
            'title': f'Augment Water Supply for {region.name}',
            'description': 'Supply augmentation required to bridge demand-supply gap.',
            'action_required': (
                'Identify and activate emergency water sources. '
                'Coordinate inter-district water transfer. '
                'Fast-track desalination or treatment plant expansion if applicable.'
            ),
        })

    if risk_level in ('MODERATE', 'HIGH', 'CRITICAL'):
        recs.append({
            'priority': 'MEDIUM' if risk_level == 'MODERATE' else 'HIGH',
            'category': 'monitoring',
            'title': f'Increase Monitoring Frequency in {region.name}',
            'description': 'Enhanced monitoring needed for early warning.',
            'action_required': (
                'Install additional IoT water level sensors at reservoirs. '
                'Increase groundwater measurement frequency to daily. '
                'Set up automated alerts for threshold breaches.'
            ),
        })
        recs.append({
            'priority': 'MEDIUM',
            'category': 'planning',
            'title': f'Develop Drought Contingency Plan for {region.name}',
            'description': 'A formal contingency plan is required.',
            'action_required': (
                'Convene district water authority meeting. '
                'Map vulnerable populations and priority supply areas. '
                'Pre-position water distribution equipment.'
            ),
        })

    if risk_level == 'LOW':
        recs.append({
            'priority': 'LOW',
            'category': 'conservation',
            'title': f'Public Awareness Campaign for {region.name}',
            'description': 'Leverage favourable conditions to build long-term water savings habits.',
            'action_required': (
                'Run community-level water conservation workshops. '
                'Promote drip irrigation among farmers. '
                'Distribute water-saving fixtures to households.'
            ),
        })

    return recs


class Command(BaseCommand):
    help = 'Seed AquaGuard AI with realistic demo data for 8 Gujarat regions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing demo data before seeding.',
        )

    def handle(self, *args, **options):
        rng = np.random.default_rng(seed=42)
        random.seed(42)

        if options['reset']:
            self.stdout.write('Deleting existing demo data ...')
            Alert.objects.filter(region__name__in=[r['name'] for r in GUJARAT_REGIONS]).delete()
            Recommendation.objects.filter(region__name__in=[r['name'] for r in GUJARAT_REGIONS]).delete()
            WaterPrediction.objects.filter(
                region__name__in=[r['name'] for r in GUJARAT_REGIONS],
                is_demo=True,
            ).delete()
            WaterMeasurement.objects.filter(
                region__name__in=[r['name'] for r in GUJARAT_REGIONS],
                is_demo_data=True,
            ).delete()
            WeatherMeasurement.objects.filter(
                region__name__in=[r['name'] for r in GUJARAT_REGIONS],
                is_demo_data=True,
            ).delete()
            self.stdout.write(self.style.WARNING('  Demo data deleted.'))

        self.stdout.write(self.style.SUCCESS('\n=== AquaGuard AI — Seeding Demo Data ===\n'))

        # ------------------------------------------------------------------
        # Step 1: Create regions
        # ------------------------------------------------------------------
        self.stdout.write('Step 1: Creating regions ...')
        region_objects = {}
        for rdef in GUJARAT_REGIONS:
            region, created = Region.objects.get_or_create(
                name=rdef['name'],
                defaults={
                    'state': rdef['state'],
                    'country': 'India',
                    'latitude': rdef['latitude'],
                    'longitude': rdef['longitude'],
                    'population': rdef['population'],
                    'area_sq_km': rdef['area_sq_km'],
                    'is_active': True,
                },
            )
            region_objects[rdef['name']] = (region, rdef['profile'])
            status = 'created' if created else 'exists'
            self.stdout.write(f'  {region.name} ({status})')

        # ------------------------------------------------------------------
        # Step 2: Generate 180 days of measurements
        # ------------------------------------------------------------------
        self.stdout.write('\nStep 2: Generating 180 days of water & weather measurements ...')
        start_date = date.today() - timedelta(days=180)

        all_measurements_by_region = {}

        for region_name, (region, profile) in region_objects.items():
            params = PROFILE_PARAMS[profile]
            self.stdout.write(f'  {region_name} ({profile}) ...', ending='')

            records = _generate_time_series(params, 180, start_date, rng)
            all_measurements_by_region[region_name] = records

            water_batch = []
            weather_batch = []
            for rec in records:
                water_batch.append(WaterMeasurement(
                    region=region,
                    date=rec['date'],
                    reservoir_level=rec['reservoir_level'],
                    reservoir_capacity_mcm=rec['reservoir_capacity_mcm'],
                    current_storage_mcm=rec['current_storage_mcm'],
                    rainfall_mm=rec['rainfall_mm'],
                    water_consumption_mld=rec['water_consumption_mld'],
                    groundwater_level_m=rec['groundwater_level_m'],
                    inflow_mcm=rec['inflow_mcm'],
                    outflow_mcm=rec['outflow_mcm'],
                    is_demo_data=True,
                ))
                weather_batch.append(WeatherMeasurement(
                    region=region,
                    date=rec['date'],
                    temperature_celsius=rec['temperature_celsius'],
                    humidity_percent=rec['humidity_percent'],
                    wind_speed_kmh=rec['wind_speed_kmh'],
                    is_demo_data=True,
                ))

            # Bulk insert, ignore conflicts from existing rows
            WaterMeasurement.objects.bulk_create(water_batch, ignore_conflicts=True)
            WeatherMeasurement.objects.bulk_create(weather_batch, ignore_conflicts=True)
            self.stdout.write(f' {len(records)} days.')

        # ------------------------------------------------------------------
        # Step 3: Create predictions (7, 14, 30 day horizons per region)
        # ------------------------------------------------------------------
        self.stdout.write('\nStep 3: Creating predictions & risk assessments ...')

        predictions_by_region = {}

        for region_name, (region, profile) in region_objects.items():
            records = all_measurements_by_region[region_name]
            # Most-recent first for factor computation
            reversed_records = list(reversed(records))

            factors = _compute_factors(reversed_records)
            risk_prob = sum(factors[k] * w for k, w in RISK_WEIGHTS.items())
            risk_prob = round(min(1.0, max(0.0, risk_prob)), 4)
            risk_level = _risk_level_from_prob(risk_prob)

            predictions_by_region[region_name] = []

            for horizon in HORIZON_DAYS:
                latest = reversed_records[0] if reversed_records else {}
                current_level = latest.get('reservoir_level', 50.0) if latest else 50.0

                if len(reversed_records) >= 7:
                    recent_7 = reversed_records[:7]
                    avg_delta = (recent_7[0]['reservoir_level'] - recent_7[-1]['reservoir_level']) / 7
                    predicted_reservoir = max(0, min(100, current_level - avg_delta * horizon))
                else:
                    predicted_reservoir = current_level

                avg_consumption = (
                    sum(m['water_consumption_mld'] for m in reversed_records[:7]) / 7
                    if len(reversed_records) >= 7 else 250.0
                )

                expected_shortage_start = None
                if risk_level in ('HIGH', 'CRITICAL'):
                    days_to = max(1, int((current_level / 100.0) * 30))
                    expected_shortage_start = date.today() + timedelta(days=days_to)

                pred = WaterPrediction.objects.create(
                    region=region,
                    horizon_days=horizon,
                    risk_probability=risk_prob,
                    risk_level=risk_level,
                    predicted_reservoir_level=round(predicted_reservoir, 2),
                    predicted_consumption=round(avg_consumption, 2),
                    expected_shortage_start=expected_shortage_start,
                    model_version='1.0.0-demo',
                    is_demo=True,
                )

                explanation = _explanation(region_name, risk_level, factors, predicted_reservoir)
                risk_score = round(risk_prob * 100, 2)
                contributing = {
                    k: round(factors[k] * RISK_WEIGHTS[k] / risk_prob * 100, 1) if risk_prob > 0 else 0
                    for k in factors
                }

                RiskAssessment.objects.create(
                    prediction=pred,
                    risk_score=risk_score,
                    rainfall_factor=factors['rainfall_factor'],
                    reservoir_factor=factors['reservoir_factor'],
                    consumption_factor=factors['consumption_factor'],
                    temperature_factor=factors['temperature_factor'],
                    demand_factor=factors['demand_factor'],
                    contributing_factors=contributing,
                    explanation_text=explanation,
                )

                predictions_by_region[region_name].append(pred)

            self.stdout.write(
                f'  {region_name}: {risk_level} risk ({risk_prob:.0%}) — {len(HORIZON_DAYS)} predictions created.'
            )

        # ------------------------------------------------------------------
        # Step 4: Create recommendations
        # ------------------------------------------------------------------
        self.stdout.write('\nStep 4: Creating recommendations ...')
        for region_name, (region, profile) in region_objects.items():
            preds = predictions_by_region[region_name]
            primary_pred = preds[0] if preds else None
            risk_level = primary_pred.risk_level if primary_pred else 'LOW'

            recs = _get_recommendations(region, primary_pred, risk_level, profile)
            for rec_data in recs:
                Recommendation.objects.create(
                    region=region,
                    prediction=primary_pred,
                    priority=rec_data['priority'],
                    category=rec_data['category'],
                    title=rec_data['title'],
                    description=rec_data['description'],
                    action_required=rec_data['action_required'],
                    is_active=True,
                )
            self.stdout.write(f'  {region_name}: {len(recs)} recommendation(s).')

        # ------------------------------------------------------------------
        # Step 5: Create alerts for high-risk regions
        # ------------------------------------------------------------------
        self.stdout.write('\nStep 5: Creating alerts ...')
        for region_name, (region, profile) in region_objects.items():
            preds = predictions_by_region[region_name]
            primary_pred = preds[0] if preds else None
            risk_level = primary_pred.risk_level if primary_pred else 'LOW'

            alerts_created = 0

            if risk_level in ('HIGH', 'CRITICAL'):
                Alert.objects.create(
                    region=region,
                    severity='CRITICAL' if risk_level == 'CRITICAL' else 'HIGH',
                    alert_type='prediction',
                    title=f'{risk_level} Water Shortage Risk — {region_name}',
                    message=(
                        f'{region_name} has been assessed as {risk_level} risk for water shortage '
                        f'with a risk probability of {primary_pred.risk_probability:.0%}. '
                        f'Predicted reservoir level: {primary_pred.predicted_reservoir_level:.1f}%. '
                        'Immediate attention required.'
                    ),
                    is_read=False,
                    is_active=True,
                )
                alerts_created += 1

                # Check reservoir level
                records = all_measurements_by_region[region_name]
                if records:
                    latest_level = records[-1]['reservoir_level']
                    if latest_level < 35.0:
                        Alert.objects.create(
                            region=region,
                            severity='WARNING',
                            alert_type='reservoir',
                            title=f'Low Reservoir Level — {region_name}',
                            message=(
                                f'Reservoir at {region_name} is at {latest_level:.1f}% capacity. '
                                'This is below the safe threshold of 35%.'
                            ),
                            is_read=False,
                            is_active=True,
                        )
                        alerts_created += 1

            elif risk_level == 'MODERATE':
                Alert.objects.create(
                    region=region,
                    severity='WARNING',
                    alert_type='prediction',
                    title=f'Moderate Water Stress Detected — {region_name}',
                    message=(
                        f'{region_name} shows moderate water stress indicators. '
                        f'Risk probability: {primary_pred.risk_probability:.0%}. '
                        'Monitor closely and prepare contingency measures.'
                    ),
                    is_read=False,
                    is_active=True,
                )
                alerts_created += 1

            else:
                # Info alert for low-risk regions
                Alert.objects.create(
                    region=region,
                    severity='INFO',
                    alert_type='general',
                    title=f'Normal Water Conditions — {region_name}',
                    message=(
                        f'{region_name} is in normal condition. '
                        f'Risk probability: {primary_pred.risk_probability:.0%}. '
                        'Continue routine monitoring.'
                    ),
                    is_read=True,  # pre-read for info alerts
                    is_active=True,
                )
                alerts_created += 1

            self.stdout.write(f'  {region_name}: {alerts_created} alert(s) [{risk_level}].')

        # ------------------------------------------------------------------
        # Done
        # ------------------------------------------------------------------
        self.stdout.write(self.style.SUCCESS('\n=== Seeding complete! ==='))
        self.stdout.write(f'Regions:         {Region.objects.count()}')
        self.stdout.write(f'Water records:   {WaterMeasurement.objects.filter(is_demo_data=True).count()}')
        self.stdout.write(f'Weather records: {WeatherMeasurement.objects.filter(is_demo_data=True).count()}')
        self.stdout.write(f'Predictions:     {WaterPrediction.objects.filter(is_demo=True).count()}')
        self.stdout.write(f'Recommendations: {Recommendation.objects.count()}')
        self.stdout.write(f'Alerts:          {Alert.objects.count()}')
