"""
Feature definitions and engineering for the AquaGuard ML pipeline.
"""
import pandas as pd
import numpy as np


FEATURE_COLUMNS = [
    'rainfall_mm', 'temperature_celsius', 'humidity_percent',
    'reservoir_level', 'water_consumption_mld', 'groundwater_level_m',
    'inflow_mcm', 'outflow_mcm',
    'rainfall_deviation', 'consumption_growth', 'reservoir_change_rate',
    'temp_anomaly', 'demand_growth', 'water_balance',
    'month', 'day_of_year', 'season',
]

TARGET_RISK_LEVEL = 'risk_level'
TARGET_RISK_PROB = 'risk_probability'


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived features from raw measurements."""
    if df.empty:
        return df

    df = df.copy()

    # Sort so rolling windows are temporally ordered (per region if available)
    sort_cols = ['region_id', 'date'] if 'region_id' in df.columns else ['date']
    df.sort_values(sort_cols, inplace=True)
    df.reset_index(drop=True, inplace=True)

    def _compute(group: pd.DataFrame) -> pd.DataFrame:
        group = group.copy()

        # rainfall_deviation: (rainfall - 30-day rolling mean) / 30-day rolling mean
        rolling_rain = group['rainfall_mm'].rolling(30, min_periods=1).mean()
        group['rainfall_deviation'] = (
            (group['rainfall_mm'] - rolling_rain) / rolling_rain.replace(0, np.nan)
        ).fillna(0)

        # consumption_growth: 7-day percent change
        group['consumption_growth'] = group['water_consumption_mld'].pct_change(7).fillna(0)

        # reservoir_change_rate: 7-day diff
        group['reservoir_change_rate'] = group['reservoir_level'].diff(7).fillna(0)

        # temp_anomaly: temperature - 30-day rolling mean
        rolling_temp = group['temperature_celsius'].rolling(30, min_periods=1).mean()
        group['temp_anomaly'] = (group['temperature_celsius'] - rolling_temp).fillna(0)

        # demand_growth: 30-day percent change of consumption
        group['demand_growth'] = group['water_consumption_mld'].pct_change(30).fillna(0)

        # water_balance: inflow - outflow
        group['water_balance'] = group['inflow_mcm'] - group['outflow_mcm']

        return group

    if 'region_id' in df.columns:
        df = df.groupby('region_id', group_keys=False).apply(_compute)
    else:
        df = _compute(df)

    return df


def compute_risk_label(df: pd.DataFrame) -> pd.DataFrame:
    """Compute risk_score, risk_level, and risk_probability columns."""
    if df.empty:
        return df

    df = df.copy()

    reservoir_component = (100 - df['reservoir_level']).clip(0, 100)

    rain_norm = (df['rainfall_mm'] / 5).clip(0, 100)
    rainfall_component = (100 - rain_norm).clip(0, 100)

    consumption_component = (df['consumption_growth'].fillna(0) * 100 + 50).clip(0, 100)

    temp_component = (df['temp_anomaly'].fillna(0) * 5 + 50).clip(0, 100)

    demand_component = (df['demand_growth'].fillna(0) * 100 + 50).clip(0, 100)

    risk_score = (
        0.35 * reservoir_component
        + 0.25 * rainfall_component
        + 0.20 * consumption_component
        + 0.10 * temp_component
        + 0.10 * demand_component
    ).clip(0, 100)

    df['risk_probability'] = (risk_score / 100.0).round(4)

    def _level(score):
        if score <= 25:
            return 'LOW'
        elif score <= 50:
            return 'MODERATE'
        elif score <= 75:
            return 'HIGH'
        else:
            return 'CRITICAL'

    df['risk_level'] = risk_score.apply(_level)

    return df
