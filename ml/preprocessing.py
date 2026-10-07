"""
WaterDataPreprocessor: loads, cleans, encodes, and scales water/weather data.
Django models are only accessed when called from within a Django process
(manage.py, WSGI, or after django.setup() is called).
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler


class WaterDataPreprocessor:
    def __init__(self):
        self.scaler = StandardScaler()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_from_db(self, region_id=None, days=180) -> pd.DataFrame:
        """Query WaterMeasurement + WeatherMeasurement and return a merged DataFrame."""
        from django.utils import timezone
        from apps.water_data.models import WaterMeasurement, WeatherMeasurement

        cutoff = timezone.now().date() - pd.Timedelta(days=days)

        water_qs = WaterMeasurement.objects.filter(date__gte=cutoff)
        weather_qs = WeatherMeasurement.objects.filter(date__gte=cutoff)

        if region_id is not None:
            water_qs = water_qs.filter(region_id=region_id)
            weather_qs = weather_qs.filter(region_id=region_id)

        water_fields = [
            'region_id', 'date', 'reservoir_level', 'reservoir_capacity_mcm',
            'current_storage_mcm', 'rainfall_mm', 'water_consumption_mld',
            'groundwater_level_m', 'inflow_mcm', 'outflow_mcm',
        ]
        weather_fields = [
            'region_id', 'date', 'temperature_celsius', 'humidity_percent',
            'wind_speed_kmh',
        ]

        water_df = pd.DataFrame(list(water_qs.values(*water_fields)))
        weather_df = pd.DataFrame(list(weather_qs.values(*weather_fields)))

        if water_df.empty:
            return pd.DataFrame()

        water_df['date'] = pd.to_datetime(water_df['date'])

        if not weather_df.empty:
            weather_df['date'] = pd.to_datetime(weather_df['date'])
            df = pd.merge(water_df, weather_df, on=['region_id', 'date'], how='left')
        else:
            df = water_df
            for col in ['temperature_celsius', 'humidity_percent', 'wind_speed_kmh']:
                df[col] = np.nan

        df.sort_values(['region_id', 'date'], inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def load_from_csv(self, filepath) -> pd.DataFrame:
        """Load CSV, validate required columns, and parse dates."""
        required_cols = [
            'date', 'rainfall_mm', 'temperature_celsius', 'humidity_percent',
            'reservoir_level', 'water_consumption_mld', 'groundwater_level_m',
            'inflow_mcm', 'outflow_mcm',
        ]
        df = pd.read_csv(filepath, parse_dates=['date'])
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")
        df.sort_values('date', inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values and clip numeric outliers."""
        if df.empty:
            return df

        df = df.copy()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        # Forward fill then backfill within each region group if region_id exists
        if 'region_id' in df.columns:
            df[numeric_cols] = (
                df.groupby('region_id')[numeric_cols]
                .transform(lambda s: s.ffill().bfill())
            )
        else:
            df[numeric_cols] = df[numeric_cols].ffill().bfill()

        # Clip outliers at 1st / 99th percentile
        for col in numeric_cols:
            lo = df[col].quantile(0.01)
            hi = df[col].quantile(0.99)
            df[col] = df[col].clip(lower=lo, upper=hi)

        return df

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def encode(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add temporal features; encode season; one-hot encode region."""
        if df.empty:
            return df

        df = df.copy()

        if 'date' in df.columns:
            df['month'] = df['date'].dt.month
            df['day_of_year'] = df['date'].dt.dayofyear

            def _season(month):
                if month in (12, 1, 2):
                    return 0   # winter
                elif month in (3, 4, 5):
                    return 1   # spring
                elif month in (6, 7, 8):
                    return 2   # summer (pre-monsoon)
                elif month in (7, 8, 9):
                    return 3   # monsoon
                else:
                    return 4   # autumn

            df['season'] = df['month'].apply(_season)

        if 'region_id' in df.columns:
            region_dummies = pd.get_dummies(df['region_id'], prefix='region', dtype=int)
            df = pd.concat([df, region_dummies], axis=1)

        return df

    # ------------------------------------------------------------------
    # Scaling
    # ------------------------------------------------------------------

    def scale(self, df: pd.DataFrame, feature_cols: list, fit: bool = True):
        """Fit/transform (fit=True) or transform-only (fit=False). Returns (df, scaler)."""
        df = df.copy()
        present_cols = [c for c in feature_cols if c in df.columns]

        if fit:
            df[present_cols] = self.scaler.fit_transform(df[present_cols])
        else:
            df[present_cols] = self.scaler.transform(df[present_cols])

        return df, self.scaler
