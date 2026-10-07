import csv
import io
from datetime import datetime
from apps.regions.models import Region
from .models import WaterMeasurement, WeatherMeasurement

REQUIRED_COLUMNS = {
    'date', 'region', 'rainfall_mm', 'temperature_celsius',
    'humidity_percent', 'reservoir_level', 'water_consumption_mld',
    'groundwater_level_m', 'inflow_mcm', 'outflow_mcm',
}

NUMERIC_FIELDS = {
    'rainfall_mm': (0, 500),
    'temperature_celsius': (-5, 55),
    'humidity_percent': (0, 100),
    'reservoir_level': (0, 100),
    'water_consumption_mld': (0, 10000),
    'groundwater_level_m': (0, 200),
    'inflow_mcm': (0, 10000),
    'outflow_mcm': (0, 10000),
}


def validate_row(row, row_num, region_map):
    """Validate a single CSV row. Returns (cleaned_data_dict, error_message_or_None)."""
    errors = []

    # Validate date
    date_str = row.get('date', '').strip()
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        errors.append(f'Row {row_num}: Invalid date format "{date_str}" (expected YYYY-MM-DD)')
        date = None

    # Validate region
    region_name = row.get('region', '').strip()
    region = region_map.get(region_name.lower())
    if region is None:
        errors.append(f'Row {row_num}: Unknown region "{region_name}"')

    # Validate numeric fields
    numeric_values = {}
    for field, (min_val, max_val) in NUMERIC_FIELDS.items():
        raw = row.get(field, '').strip()
        try:
            val = float(raw)
            if not (min_val <= val <= max_val):
                errors.append(
                    f'Row {row_num}: {field} value {val} out of range [{min_val}, {max_val}]'
                )
            numeric_values[field] = val
        except (ValueError, TypeError):
            errors.append(f'Row {row_num}: Invalid numeric value for {field}: "{raw}"')
            numeric_values[field] = None

    if errors:
        return None, errors

    # Additional derived fields
    reservoir_capacity = numeric_values['reservoir_level']  # use level as proxy if capacity not provided
    current_storage = (numeric_values['reservoir_level'] / 100.0) * 1000.0  # rough estimate in MCM

    return {
        'date': date,
        'region': region,
        'rainfall_mm': numeric_values['rainfall_mm'],
        'temperature_celsius': numeric_values['temperature_celsius'],
        'humidity_percent': numeric_values['humidity_percent'],
        'reservoir_level': numeric_values['reservoir_level'],
        'reservoir_capacity_mcm': 1000.0,
        'current_storage_mcm': current_storage,
        'water_consumption_mld': numeric_values['water_consumption_mld'],
        'groundwater_level_m': numeric_values['groundwater_level_m'],
        'inflow_mcm': numeric_values['inflow_mcm'],
        'outflow_mcm': numeric_values['outflow_mcm'],
    }, None


def import_csv(file_obj, is_demo_data=False):
    """
    Import water and weather data from a CSV file object.

    Returns:
        (success_count, error_list)
    """
    errors = []
    success_count = 0

    try:
        if hasattr(file_obj, 'read'):
            content = file_obj.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
        else:
            content = file_obj

        reader = csv.DictReader(io.StringIO(content))
    except Exception as e:
        return 0, [f'Failed to parse CSV file: {e}']

    # Validate headers
    if reader.fieldnames is None:
        return 0, ['CSV file is empty or has no headers.']

    actual_columns = {col.strip().lower() for col in reader.fieldnames}
    missing = REQUIRED_COLUMNS - actual_columns
    if missing:
        return 0, [f'CSV is missing required columns: {", ".join(sorted(missing))}']

    # Build region lookup (case-insensitive)
    region_map = {r.name.lower(): r for r in Region.objects.all()}

    rows = list(reader)
    if not rows:
        return 0, ['CSV file contains no data rows.']

    for row_num, row in enumerate(rows, start=2):
        # Normalise keys
        norm_row = {k.strip().lower(): v for k, v in row.items() if k}
        cleaned, row_errors = validate_row(norm_row, row_num, region_map)
        if row_errors:
            errors.extend(row_errors)
            continue

        try:
            # Upsert WaterMeasurement
            WaterMeasurement.objects.update_or_create(
                region=cleaned['region'],
                date=cleaned['date'],
                defaults={
                    'reservoir_level': cleaned['reservoir_level'],
                    'reservoir_capacity_mcm': cleaned['reservoir_capacity_mcm'],
                    'current_storage_mcm': cleaned['current_storage_mcm'],
                    'rainfall_mm': cleaned['rainfall_mm'],
                    'water_consumption_mld': cleaned['water_consumption_mld'],
                    'groundwater_level_m': cleaned['groundwater_level_m'],
                    'inflow_mcm': cleaned['inflow_mcm'],
                    'outflow_mcm': cleaned['outflow_mcm'],
                    'is_demo_data': is_demo_data,
                }
            )

            # Upsert WeatherMeasurement
            WeatherMeasurement.objects.update_or_create(
                region=cleaned['region'],
                date=cleaned['date'],
                defaults={
                    'temperature_celsius': cleaned['temperature_celsius'],
                    'humidity_percent': cleaned['humidity_percent'],
                    'wind_speed_kmh': 15.0,  # default when not in CSV
                    'is_demo_data': is_demo_data,
                }
            )
            success_count += 1
        except Exception as e:
            errors.append(f'Row {row_num}: Database error — {e}')

    return success_count, errors
