# AquaGuard AI — Water Crisis Prediction Platform

> **Predict. Prepare. Preserve.**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2.7-green.svg)](https://djangoproject.com)
[![Deployment](https://img.shields.io/badge/Deployment-Render-informational.svg)](https://render.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Live Application
- **Live Demo**: `https://<your-app-name>.onrender.com` *(Replace with your Render deployment URL after setup)*

---

## Overview

AquaGuard AI is an intelligent water crisis early-warning platform that leverages machine learning and rule-based AI to predict water shortage risks up to 30 days ahead across multiple regions. It provides water resource managers and municipal authorities with regional risk scores, interactive maps, automated alerts, actionable recommendations, downloadable PDF executive reports, and water/weather telemetry monitoring — all through a responsive web application and secure Django admin panel.

---

## Key Features

- **Water Crisis Prediction (up to 30 days ahead)**: Dual-model risk engine utilizing Random Forest ML models (`scikit-learn`) with rule-based fallback to forecast shortage risk levels (Low, Moderate, High, Critical) for 7-day, 14-day, and 30-day horizons.
- **Interactive Water Risk Map**: Leaflet.js map with color-coded regional status markers for quick visual risk assessment across monitoring locations.
- **Executive Dashboard**: Unified overview of risk distribution across regions, trend analysis charts (Chart.js), recent recommendations, and critical alert feeds.
- **Telemetry & Data Management**: Track reservoir capacity, daily consumption, rainfall deficits, temperature anomalies, and groundwater levels. Supports bulk CSV dataset imports with validation.
- **Downloadable PDF Reports**: Automated, professional PDF briefing reports generated using ReportLab for stakeholder updates.
- **Alert & Recommendation Engine**: Automated system alert triggers categorized by severity (Info, Warning, High, Critical) and priority-ranked mitigation recommendations.
- **IBM watsonx.ai Integration**: Optional LLM enhancement (IBM Granite) for natural language risk explanations and advisory insights when credentials are configured.
- **Django Admin & API**: Full administrative management via `/admin/`. Public login/register forms have been removed for streamlined public portal access and secure backend administration.

---

## Technology Stack

| Component | Technology |
| --- | --- |
| **Backend Framework** | Python 3.12, Django 4.2.7, Django REST Framework 3.14.0 |
| **Production Server** | Gunicorn 26.2.0, WhiteNoise 6.12.0 (Static File Handling) |
| **Database** | SQLite (development) / PostgreSQL (production via `dj-database-url`) |
| **Machine Learning & Data** | scikit-learn 1.3.2, pandas 2.1.3, numpy 1.26.2, joblib 1.3.2 |
| **Frontend & UI** | HTML5, Vanilla CSS, Bootstrap 5.3, Chart.js 4, Leaflet.js 1.9 |
| **PDF Generation** | ReportLab 4.0.7, Pillow 10.1.0 |
| **AI Integration** | `requests` (IBM watsonx.ai API interface) |

---

## Environment Variables

Configure the following variables in a `.env` file locally or in the Render environment settings:

| Variable | Required | Default / Example | Description |
| --- | --- | --- | --- |
| `SECRET_KEY` | **Yes** | *(random 50+ char string)* | Django cryptographic signing key |
| `DEBUG` | **Yes (Prod)** | `False` (`True` in dev) | Django debug mode |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated allowed hostnames |
| `DATABASE_URL` | Prod | `sqlite:///db.sqlite3` | Database connection URL (PostgreSQL on Render) |
| `RENDER_EXTERNAL_HOSTNAME` | Prod | `aquaguard.onrender.com` | Set automatically by Render |
| `PYTHON_VERSION` | Prod | `3.12.10` | Python runtime version for Render build |
| `DJANGO_SUPERUSER_USERNAME` | Prod | `admin` | Username for automated superuser creation on deploy |
| `DJANGO_SUPERUSER_EMAIL` | Prod | `admin@aquaguard.ai` | Email for automated superuser creation on deploy |
| `DJANGO_SUPERUSER_PASSWORD` | Prod | `ChangeMeSecurePass123!` | Password for automated superuser creation on deploy |
| `IBM_API_KEY` | Optional | `""` | IBM watsonx.ai API key for LLM explanations |
| `IBM_PROJECT_ID` | Optional | `""` | IBM watsonx.ai project ID |
| `IBM_URL` | Optional | `""` | IBM watsonx.ai service endpoint URL |

---

## Local Setup (Windows)

### 1. Prerequisites
- Python 3.12 installed
- Git

### 2. Activate Virtual Environment & Install Dependencies
```powershell
# Activate local virtual environment
.\venv\Scripts\activate

# Install requirements
.\venv\Scripts\pip.exe install -r requirements.txt
```

### 3. Configure Environment File
Create a `.env` file in the project root:
```env
SECRET_KEY=django-insecure-aquaguard-local-dev-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 4. Database Setup & Demo Data
```powershell
# Run database migrations
.\venv\Scripts\python.exe manage.py migrate

# Seed sample data for 10 Indian cities
.\venv\Scripts\python.exe manage.py seed_demo_data

# Train machine learning models
.\venv\Scripts\python.exe manage.py train_models
```

### 5. Create Superuser (Django Admin)
```powershell
.\venv\Scripts\python.exe manage.py createsuperuser
```
Follow the interactive prompts to set your administrative username, email, and password.

### 6. Run the Development Server
```powershell
.\venv\Scripts\python.exe manage.py runserver
```

Open your browser to:
- **Landing Page**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Dashboard**: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
- **Predictions**: [http://127.0.0.1:8000/predictions/](http://127.0.0.1:8000/predictions/)
- **Admin Panel**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## Deployment Notes (Render)

To deploy AquaGuard AI on **Render Free Tier**:

### 1. Web Service Configuration
- **Runtime**: Python 3
- **Build Command**:
  ```bash
  pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate && (python manage.py createsuperuser --noinput || true)
  ```
- **Start Command**:
  ```bash
  gunicorn config.wsgi:application
  ```

### 2. Environment Variables on Render
Set the following environment variables in the Render Dashboard under **Environment**:
- `SECRET_KEY`: *(Generate a secure random string)*
- `DEBUG`: `False`
- `PYTHON_VERSION`: `3.12.10`
- `DJANGO_SUPERUSER_USERNAME`: `admin`
- `DJANGO_SUPERUSER_EMAIL`: `admin@aquaguard.ai`
- `DJANGO_SUPERUSER_PASSWORD`: *(Your strong production password)*

---

## Project Structure

```
aquaguard/
├── apps/
│   ├── accounts/         User profile models and helper functions
│   ├── alerts/           Alert models, views, and API endpoints
│   ├── api/              DRF router and centralized API config
│   ├── dashboard/        Executive dashboard and settings views
│   ├── predictions/      Prediction views, horizons, and explanations
│   ├── recommendations/  Mitigation recommendation models and views
│   ├── regions/          Region models, Leaflet map views, and management commands
│   ├── reports/          ReportLab PDF generation service
│   └── water_data/       Measurement models, CSV importer, and data views
├── config/               Django settings, URL routing, and WSGI/ASGI apps
├── ml/                   ML pipeline (features.py, train.py, predict.py, risk_engine.py)
├── services/             AI Provider abstraction layer (IBM watsonx / Local fallback)
├── static/               CSS, JavaScript, and static assets
├── templates/            HTML templates (landing page, dashboard, reports, admin base)
├── .gitignore            Git exclusions file
├── manage.py             Django management script
├── requirements.txt      Pinned production dependencies
└── README.md             Project documentation
```

---

## License

MIT License — see `LICENSE` for details.
