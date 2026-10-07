"""
Management command: train_models
Trains the risk classifier and shortage probability regressor
using data from the database.

Usage:
    python manage.py train_models
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Train AquaGuard ML models (risk classifier + shortage regressor)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Number of days of historical data to use for training (default: 365)',
        )

    def handle(self, *args, **options):
        days = options['days']
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'AquaGuard ML Training — using {days} days of data'
        ))

        try:
            import pandas as pd  # noqa: F401 — validate dependency early
        except ImportError:
            self.stderr.write(self.style.ERROR('pandas is required. Run: pip install pandas scikit-learn joblib'))
            return

        from ml.preprocessing import WaterDataPreprocessor
        from ml.features import engineer_features, compute_risk_label
        from ml.train import (
            train_risk_classifier,
            train_shortage_probability_regressor,
            REPORT_PATH,
        )
        import json

        self.stdout.write('Loading data from database...')
        preprocessor = WaterDataPreprocessor()
        raw_df = preprocessor.load_from_db(days=days)

        if raw_df.empty:
            self.stderr.write(self.style.ERROR(
                'No data found. Run `python manage.py seed_demo_data` first.'
            ))
            return

        self.stdout.write(f'  Loaded {len(raw_df)} rows.')

        df = preprocessor.clean(raw_df)
        df = preprocessor.encode(df)
        df = engineer_features(df)
        df = compute_risk_label(df)

        self.stdout.write(f'  After preprocessing: {len(df)} rows, {len(df.columns)} columns.')
        if 'risk_level' in df.columns:
            dist = df['risk_level'].value_counts().to_dict()
            self.stdout.write(f'  Risk distribution: {dist}')

        report = {}

        self.stdout.write(self.style.MIGRATE_HEADING('\nTraining risk classifier...'))
        try:
            metrics = train_risk_classifier(df)
            report['risk_classifier'] = metrics
            self.stdout.write(self.style.SUCCESS(
                f"  ✓ Accuracy: {metrics['accuracy']:.4f}  F1 (wtd): {metrics['f1_weighted']:.4f}"
            ))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'  ✗ Failed: {exc}'))
            report['risk_classifier'] = {'error': str(exc)}

        self.stdout.write(self.style.MIGRATE_HEADING('\nTraining shortage regressor...'))
        try:
            metrics = train_shortage_probability_regressor(df)
            report['shortage_regressor'] = metrics
            self.stdout.write(self.style.SUCCESS(
                f"  ✓ MAE: {metrics['mae']:.4f}  RMSE: {metrics['rmse']:.4f}  R²: {metrics['r2']:.4f}"
            ))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'  ✗ Failed: {exc}'))
            report['shortage_regressor'] = {'error': str(exc)}

        with open(REPORT_PATH, 'w') as fh:
            json.dump(report, fh, indent=2)

        self.stdout.write(self.style.SUCCESS(f'\nTraining report saved to {REPORT_PATH}'))
        self.stdout.write(self.style.SUCCESS('Done.'))
