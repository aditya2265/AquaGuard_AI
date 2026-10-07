"""
Model training for AquaGuard ML pipeline.

Run standalone:
    cd aquaguard
    python -m ml.train

Or via management command:
    python manage.py train_models
"""
import os
import json
import logging
from pathlib import Path

import django

# Ensure Django is set up when run as a script
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, mean_absolute_error, r2_score,
)

from ml.preprocessing import WaterDataPreprocessor
from ml.features import FEATURE_COLUMNS, TARGET_RISK_LEVEL, TARGET_RISK_PROB
from ml.features import engineer_features, compute_risk_label

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent / 'models'
MODELS_DIR.mkdir(exist_ok=True)

CLASSIFIER_PATH = MODELS_DIR / 'risk_classifier.joblib'
REGRESSOR_PATH = MODELS_DIR / 'shortage_regressor.joblib'
REPORT_PATH = MODELS_DIR / 'training_report.json'


def _prepare_data(df: pd.DataFrame):
    """Drop rows with NaN in any feature column; return X and df."""
    present = [c for c in FEATURE_COLUMNS if c in df.columns]
    valid = df.dropna(subset=present).copy()
    return valid, present


def train_risk_classifier(df: pd.DataFrame) -> dict:
    """
    Train a 4-class risk level classifier (RandomForest).
    Returns metrics dict.
    """
    valid, feature_cols = _prepare_data(df)
    if valid.empty or TARGET_RISK_LEVEL not in valid.columns:
        raise ValueError("Insufficient data or missing target column 'risk_level'.")

    X = valid[feature_cols].values
    y = valid[TARGET_RISK_LEVEL].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)),
    ])

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    metrics = {
        'model': 'RandomForestClassifier',
        'n_features': len(feature_cols),
        'n_train': len(X_train),
        'n_test': len(X_test),
        'accuracy': round(accuracy_score(y_test, y_pred), 4),
        'precision_weighted': round(precision_score(y_test, y_pred, average='weighted', zero_division=0), 4),
        'recall_weighted': round(recall_score(y_test, y_pred, average='weighted', zero_division=0), 4),
        'f1_weighted': round(f1_score(y_test, y_pred, average='weighted', zero_division=0), 4),
        'classification_report': classification_report(y_test, y_pred, zero_division=0),
    }

    joblib.dump(pipeline, CLASSIFIER_PATH)
    logger.info("Risk classifier saved to %s", CLASSIFIER_PATH)
    return metrics


def train_shortage_probability_regressor(df: pd.DataFrame) -> dict:
    """
    Train a GradientBoosting regressor for risk probability (0-1 continuous).
    Returns metrics dict.
    """
    valid, feature_cols = _prepare_data(df)
    if valid.empty or TARGET_RISK_PROB not in valid.columns:
        raise ValueError("Insufficient data or missing target column 'risk_probability'.")

    X = valid[feature_cols].values
    y = valid[TARGET_RISK_PROB].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('reg', GradientBoostingRegressor(n_estimators=100, random_state=42)),
    ])

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test).clip(0, 1)

    rmse = float(np.sqrt(((y_test - y_pred) ** 2).mean()))
    metrics = {
        'model': 'GradientBoostingRegressor',
        'n_features': len(feature_cols),
        'n_train': len(X_train),
        'n_test': len(X_test),
        'mae': round(mean_absolute_error(y_test, y_pred), 4),
        'rmse': round(rmse, 4),
        'r2': round(r2_score(y_test, y_pred), 4),
    }

    joblib.dump(pipeline, REGRESSOR_PATH)
    logger.info("Shortage regressor saved to %s", REGRESSOR_PATH)
    return metrics


def train_all():
    """
    Full training pipeline:
    1. Load data from DB via WaterDataPreprocessor
    2. Engineer features + compute risk labels
    3. Train both models
    4. Save training_report.json
    """
    print("Loading data from database...")
    preprocessor = WaterDataPreprocessor()
    raw_df = preprocessor.load_from_db(days=365)

    if raw_df.empty:
        print("ERROR: No data found in database. Run 'python manage.py seed_demo_data' first.")
        return

    print(f"Loaded {len(raw_df)} rows from DB.")

    df = preprocessor.clean(raw_df)
    df = preprocessor.encode(df)
    df = engineer_features(df)
    df = compute_risk_label(df)

    print(f"After preprocessing: {len(df)} rows, {len(df.columns)} columns")
    if TARGET_RISK_LEVEL in df.columns:
        print("Risk level distribution:\n", df[TARGET_RISK_LEVEL].value_counts().to_string())

    report = {}

    print("\nTraining risk classifier...")
    try:
        clf_metrics = train_risk_classifier(df)
        report['risk_classifier'] = clf_metrics
        print(f"  Accuracy : {clf_metrics['accuracy']:.4f}")
        print(f"  F1 (wtd) : {clf_metrics['f1_weighted']:.4f}")
    except Exception as exc:
        print(f"  FAILED: {exc}")
        report['risk_classifier'] = {'error': str(exc)}

    print("\nTraining shortage probability regressor...")
    try:
        reg_metrics = train_shortage_probability_regressor(df)
        report['shortage_regressor'] = reg_metrics
        print(f"  MAE  : {reg_metrics['mae']:.4f}")
        print(f"  RMSE : {reg_metrics['rmse']:.4f}")
        print(f"  R²   : {reg_metrics['r2']:.4f}")
    except Exception as exc:
        print(f"  FAILED: {exc}")
        report['shortage_regressor'] = {'error': str(exc)}

    with open(REPORT_PATH, 'w') as fh:
        json.dump(report, fh, indent=2)
    print(f"\nTraining report saved to {REPORT_PATH}")
    print("Done.")


if __name__ == '__main__':
    train_all()
