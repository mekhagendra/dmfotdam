# Terrorism Detection and Monitoring System (TDM)

A full-stack web data mining application that uses **machine learning** and **natural language processing** to detect and classify potential terrorism-related threats from uploaded documents, structured data files, and free-form text.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Machine Learning Pipeline](#machine-learning-pipeline)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Frontend Pages](#frontend-pages)
- [Database Schema](#database-schema)
- [Dataset & EDA](#dataset--eda)
- [Testing](#testing)
- [Docker Deployment](#docker-deployment)
- [Security](#security)
- [Documentation](#documentation)
- [License](#license)

---

## Overview

The TDM System analyzes text from multiple file formats (PDF, DOCX, TXT, CSV, Excel, JSON) and classifies content using a **hybrid approach** that combines:

1. **Rule-based keyword detection** across four threat categories (violence, extremism, planning, financing)
2. **Machine learning classification** using two scikit-learn models trained on the Global Terrorism Database (181,691 incidents from 1970–2017)

The final threat score blends both methods: **70% ML + 30% rule-based**, providing robust threat level classification (low / medium / high / critical) and attack type prediction (Bombing/Explosion, Armed Assault, Assassination, Hostage Taking, Infrastructure Attack, Unarmed Assault, Hijacking, Unknown).

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Document Upload & Analysis** | Upload PDF, DOCX, TXT, CSV, Excel, JSON files for automated threat analysis |
| **Text Analysis** | Paste and analyze free-form text directly via API or the web interface |
| **ML-Powered Classification** | TF-IDF + SGD classifier trained on GTD — 91% accuracy (threat level), 88% accuracy (attack type) |
| **Data Profiling** | Structured data files (CSV/Excel/JSON) receive full statistical profiling alongside threat analysis |
| **Interactive Dashboard** | Real-time charts, threat distribution, and analytics via Chart.js and Recharts |
| **Live Monitoring** | Configurable web source monitoring with keyword-based alerting |
| **Alert System** | Automated alert generation with threat level, source tracking, and resolution workflow |
| **User Authentication** | JWT-based authentication with role-based access (admin / analyst / viewer) |
| **Reporting** | Browse, filter, and review all historical analysis results |

---

## Architecture

```
┌──────────────────┐     ┌────────────────────┐     ┌──────────────────────┐
│  React Frontend  │────▶│   FastAPI Backend   │────▶│  ML / NLP Engine     │
│  (TypeScript +   │     │   (REST API)        │     │  (scikit-learn +     │
│   Tailwind CSS)  │     │                     │     │   TF-IDF pipeline)   │
└──────────────────┘     └────────────────────┘     └──────────────────────┘
         │                         │                          │
         ▼                         ▼                          ▼
┌──────────────────┐     ┌────────────────────┐     ┌──────────────────────┐
│  Web Browser     │     │  SQLite / Postgres  │     │  Trained Models      │
│  localhost:3000  │     │  (SQLAlchemy ORM)   │     │  (.joblib files)     │
└──────────────────┘     └────────────────────┘     └──────────────────────┘
```

---

## Technology Stack

### Backend (Python 3.11+)

| Component | Technology |
|-----------|-----------|
| Web Framework | FastAPI 0.104 + Uvicorn |
| ORM / Database | SQLAlchemy 2.0 (async) + aiosqlite (dev) / asyncpg (prod) |
| Machine Learning | scikit-learn (TfidfVectorizer + SGDClassifier), joblib |
| NLP | NLTK, langdetect, regex-based keyword matching |
| Text Extraction | PyPDF2 (PDF), python-docx (DOCX), pandas + openpyxl (CSV/Excel), json (JSON) |
| Authentication | JWT via python-jose, bcrypt password hashing |
| Web Scraping | requests, BeautifulSoup4 |
| Logging | structlog |
| Configuration | pydantic-settings + .env files |

### Frontend (Node.js 18+)

| Component | Technology |
|-----------|-----------|
| Framework | React 18 + TypeScript |
| Styling | Tailwind CSS 3.3 |
| Charts | Chart.js + react-chartjs-2, Recharts |
| Data Fetching | React Query, Axios |
| Forms & UI | react-hook-form, react-dropzone, @headlessui/react, @heroicons/react |
| Routing | react-router-dom v6 |
| Notifications | react-toastify |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Containerisation | Docker + Docker Compose |
| Reverse Proxy | Nginx (production) |
| Database (prod) | PostgreSQL 15 |
| Caching (prod) | Redis 7 |

---

## Project Structure

```
dmfotdam/
├── backend/
│   ├── main.py                        # FastAPI entry point + lifespan (DB init, ML model loading)
│   ├── requirements.txt               # Python dependencies
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py            # API router (auth, upload, detection, monitoring)
│   │   │   ├── dependencies.py        # Shared dependencies
│   │   │   └── endpoints/
│   │   │       ├── auth.py            # Register, login, profile
│   │   │       ├── upload.py          # Document upload + analysis trigger
│   │   │       ├── detection.py       # Text analysis, results, data profiling, reports
│   │   │       └── monitoring.py      # Live monitoring source management
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic settings from .env
│   │   │   ├── database.py           # Async SQLAlchemy engine, session, table creation
│   │   │   ├── security.py           # JWT creation/verification, password hashing
│   │   │   └── logging.py            # structlog configuration
│   │   ├── models/
│   │   │   ├── user.py               # User (roles: admin/analyst/viewer)
│   │   │   ├── document.py           # Uploaded document metadata
│   │   │   ├── analysis.py           # Analysis results (scores, details, keywords)
│   │   │   └── alert.py              # Threat alerts + monitoring sources
│   │   ├── services/
│   │   │   ├── text_analyzer.py       # Hybrid rule-based + ML threat analysis
│   │   │   ├── ml_service.py          # Loads and runs trained scikit-learn models
│   │   │   ├── web_scraper.py         # URL content scraping
│   │   │   └── live_monitor.py        # Background monitoring service
│   │   └── utils/
│   │       ├── file_handler.py        # File validation, save, delete
│   │       ├── text_processor.py      # Text cleaning utilities
│   │       └── validators.py          # Input validation helpers
│   ├── data/
│   │   ├── datasets/
│   │   │   ├── gtd.csv               # Global Terrorism Database (181,691 records)
│   │   │   └── eda_output/            # 15 EDA visualisation PNGs
│   │   ├── models/
│   │   │   ├── threat_level_model.joblib    # Trained threat level classifier
│   │   │   └── attack_type_model.joblib     # Trained attack type classifier
│   │   └── uploads/                   # User-uploaded files
│   ├── scripts/
│   │   ├── train_models.py            # ML model training script
│   │   ├── run_eda.py                 # Exploratory data analysis + visualisations
│   │   └── explore_data.py            # Dataset exploration utility
│   └── tests/
│       ├── test_text_analyzer.py
│       └── test_utils.py
├── frontend/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── src/
│       ├── App.tsx                    # Routes + auth guard
│       ├── index.tsx                  # React entry point
│       ├── index.css                  # Tailwind imports
│       ├── components/
│       │   ├── Layout.tsx             # Sidebar + topbar layout
│       │   ├── AlertList.tsx          # Alert display component
│       │   ├── ThreatBadge.tsx        # Colour-coded threat level badge
│       │   └── ThreatChart.tsx        # Threat distribution chart
│       ├── context/
│       │   └── AuthContext.tsx         # JWT auth state management
│       ├── hooks/
│       │   └── useDetection.ts        # React Query hooks for detection API
│       ├── pages/
│       │   ├── Dashboard.tsx          # Overview with charts and stats
│       │   ├── Upload.tsx             # Drag-and-drop file upload + text analysis
│       │   ├── Monitoring.tsx         # Live monitoring configuration
│       │   ├── Reports.tsx            # Analysis history table
│       │   └── Login.tsx              # Authentication form
│       └── services/
│           ├── api.ts                 # Axios instance + interceptors
│           ├── auth.service.ts        # Login/register/logout API calls
│           └── detection.service.ts   # Upload, analysis, and report API calls
├── docker/
│   ├── docker-compose.yml             # Multi-service orchestration
│   ├── Dockerfile.backend             # Python backend container
│   ├── Dockerfile.frontend            # React frontend container
│   └── nginx.conf                     # Production reverse proxy config
├── scripts/
│   ├── setup.sh                       # Automated project setup
│   └── start-dev.sh                   # Start backend + frontend dev servers
├── docs/
│   ├── api-documentation.md           # Complete API reference
│   ├── project-structure.md           # Architecture details
│   ├── dataset-research-and-selection.md  # Dataset evaluation and rationale
│   └── data-profiling-eda-report.md   # GTD profiling + EDA findings
└── README.md
```

---

## Machine Learning Pipeline

### Training Data

The **Global Terrorism Database (GTD)** from the University of Maryland — 181,691 terrorism incidents (1970–2017) with 135 variables. 115,562 records include text summaries used for training.

### Models

| Model | Task | Labels | Training Accuracy |
|-------|------|--------|-------------------|
| **Threat Level** | Classify severity | low, medium, high, critical | **91%** |
| **Attack Type** | Classify attack category | 8 classes (Bombing, Armed Assault, Assassination, Hostage Taking, Infrastructure Attack, Unarmed Assault, Hijacking, Unknown) | **88%** |

### Pipeline Architecture

```
Input Text
    │
    ▼
┌──────────────────────────────┐
│  TF-IDF Vectoriser           │
│  - 30,000 features           │
│  - Unigrams + bigrams        │
│  - Sublinear TF scaling      │
│  - Min doc freq: 3           │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│  SGD Classifier              │
│  - Modified Huber loss       │
│  - Balanced class weights    │
│  - Probability estimates     │
└──────────────────────────────┘
    │
    ▼
Prediction + Probabilities
```

### Label Derivation (Threat Level)

Threat level labels are derived from the total casualties (killed + wounded) per incident:

| Casualties | Threat Level |
|------------|-------------|
| 0 | Low |
| 1 – 5 | Medium |
| 6 – 20 | High |
| > 20 | Critical |

### Hybrid Scoring

The final threat score combines both methods:

```
threat_score = 0.7 × ML_score + 0.3 × rule_based_score
```

The rule-based component uses keyword density and category diversity across four threat categories (violence, extremism, planning, financing).

### Training the Models

```bash
cd backend
source venv/bin/activate
python scripts/train_models.py
```

This reads `data/datasets/gtd.csv`, trains both models, prints classification reports, and saves `.joblib` files to `data/models/`.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+

### Quick Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd dmfotdam

# 2. Run the automated setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Start development servers
./scripts/start-dev.sh
```

### Manual Setup

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Train ML models (required on first run)
python scripts/train_models.py

# Start the server
python main.py
```

**Frontend:**

```bash
cd frontend
npm install
npm start
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/api/docs |
| API Docs (ReDoc) | http://localhost:8000/api/redoc |
| Health Check | http://localhost:8000/health |

### First-Time Usage

1. **Register** a user account at the frontend login page, or via the API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "username": "admin",
       "email": "admin@example.com",
       "password": "Admin123!",
       "full_name": "Admin User"
     }'
   ```

2. **Log in** to receive a JWT token and access the dashboard.

3. **Upload** a document or paste text for threat analysis.

---

## Configuration

Create a `.env` file in the `backend/` directory (or project root):

```bash
# Application
ENVIRONMENT=development          # development | production
HOST=127.0.0.1
PORT=8000

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/tdm.db          # Development (SQLite)
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tdm_db  # Production

# Security
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_HOSTS=["http://localhost:3000","http://127.0.0.1:3000"]

# File Upload
MAX_FILE_SIZE=52428800           # 50 MB
UPLOAD_DIR=data/uploads
MODEL_DIR=data/models

# External APIs (optional)
NEWS_API_KEY=
TWITTER_BEARER_TOKEN=

# Production-only
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user (username, email, password, full_name) |
| POST | `/auth/login` | Login → returns JWT access token |
| GET | `/auth/me` | Get current user profile |

### File Upload

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload/document` | Upload file (PDF, DOCX, TXT, CSV, XLSX, XLS, JSON) for analysis |
| GET | `/upload/history` | List user's upload history |
| GET | `/upload/status/{id}` | Check upload/analysis status |

### Threat Detection

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/detection/analyze-text` | Analyze free-form text (10–50,000 chars) |
| GET | `/detection/results/{id}` | Get analysis results by ID |
| GET | `/detection/reports` | List all analysis reports |
| GET | `/detection/data-profile/{id}` | Get data profiling results for structured file uploads |

### Live Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/monitoring/sources` | List monitoring sources |
| POST | `/monitoring/sources` | Add a monitoring source |
| GET | `/monitoring/alerts` | List recent alerts |

All endpoints except `/auth/register` and `/auth/login` require a Bearer token in the `Authorization` header.

### Example: Analyse Text

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Analyse text
curl -X POST http://localhost:8000/api/v1/detection/analyze-text \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "A car bomb exploded near the government building, killing 15 people."}'
```

### Example Response

```json
{
  "id": 1,
  "analysis_type": "text",
  "status": "completed",
  "threat_score": 0.678,
  "threat_level": "high",
  "summary": "Threat level: HIGH (score: 0.68). Rule-based indicators in: violence, extremism. ML-predicted threat level: critical. ML-predicted attack type: Bombing/Explosion. Further manual review is recommended.",
  "details": {
    "keyword_hits": {
      "violence": [{"keyword": "bomb", "count": 1}]
    },
    "word_count": 12,
    "categories_detected": ["violence"],
    "ml_classification": {
      "ml_threat_level": "critical",
      "ml_threat_score": 0.8267,
      "ml_threat_probabilities": {"critical": 0.71, "high": 0.29, "low": 0.0, "medium": 0.0},
      "ml_attack_type": "Bombing/Explosion",
      "ml_attack_probabilities": {"Bombing/Explosion": 1.0, "Armed Assault": 0.0, "...": "..."}
    },
    "analysis_method": "ml_model"
  },
  "keywords": ["bomb", "exploded", "government", "building", "killing", "people"],
  "sentiment": "negative",
  "language": "en"
}
```

---

## Frontend Pages

| Page | Path | Description |
|------|------|-------------|
| **Login** | `/login` | Email/password authentication |
| **Dashboard** | `/` | Real-time threat level overview, charts (threat distribution, recent activity, stats) |
| **Upload** | `/upload` | Drag-and-drop file upload (PDF, DOCX, TXT, CSV, Excel, JSON) + paste-and-analyse text box |
| **Monitoring** | `/monitoring` | Add/manage web monitoring sources, view live alerts |
| **Reports** | `/reports` | Full analysis history with threat badges, filters, and detailed results |

All pages except Login are protected by JWT authentication.

---

## Database Schema

The system uses **SQLite** in development and **PostgreSQL** in production, with SQLAlchemy async ORM. Tables are auto-created at startup.

| Table | Key Fields | Purpose |
|-------|------------|---------|
| `users` | username, email, hashed_password, role, is_active | User authentication and RBAC |
| `documents` | filename, file_type, file_size, file_path, status, uploaded_by | Uploaded file metadata |
| `analyses` | document_id, threat_score, threat_level, summary, details (JSON), keywords (JSON), sentiment | Analysis results |
| `alerts` | title, threat_level, threat_score, source, source_type, is_read, is_resolved | Threat alerts |
| `monitoring_sources` | name, url, source_type, keywords (JSON), check_interval, is_active | Web monitoring configuration |

---

## Dataset & EDA

### Global Terrorism Database (GTD)

- **Source:** University of Maryland, via Kaggle
- **Records:** 181,691 incidents (1970–2017)
- **Variables:** 135 columns including event summaries, attack types, weapon types, target types, casualties, geographic data
- **Text field:** `summary` column (115,562 non-null) — used for ML training

### Exploratory Data Analysis

15 visualisations generated by `scripts/run_eda.py` and saved to `data/datasets/eda_output/`:

| # | Visualisation |
|---|---------------|
| 01 | Yearly trend of attacks |
| 02 | Top affected countries |
| 03 | Attack type distribution |
| 04 | Target type distribution |
| 05 | Weapon type distribution |
| 06 | Regional analysis |
| 07 | Casualty analysis |
| 08 | Most active terror groups |
| 09 | Attack success rates |
| 10 | Suicide attack analysis |
| 11 | Feature correlation heatmap |
| 12 | Missing values analysis |
| 13 | Geographic scatter map |
| 14 | Seasonal patterns |
| 15 | Feature distributions |

Full reports: [Dataset Research & Selection](docs/dataset-research-and-selection.md) · [Data Profiling & EDA Report](docs/data-profiling-eda-report.md)

---

## Testing

```bash
# Backend tests
cd backend
source venv/bin/activate
pytest tests/ -v

# Frontend tests
cd frontend
npm test
```

---

## Docker Deployment

Production deployment using Docker Compose with PostgreSQL, Redis, Nginx, and background workers:

```bash
# Build and start all services
docker-compose -f docker/docker-compose.yml up -d

# Services started:
#   postgres    → port 5432
#   redis       → port 6379
#   backend     → port 8000
#   frontend    → port 3000
#   celery      → background worker
#   nginx       → port 80/443 (production profile)
```

The backend container automatically overrides `DATABASE_URL` to use the PostgreSQL container and `REDIS_URL` to use the Redis container.

---

## Security

- **Authentication:** JWT tokens with configurable expiration (default 30 min)
- **Password Storage:** bcrypt hashing
- **CORS:** Configurable allowed origins via `ALLOWED_HOSTS`
- **Input Validation:** Pydantic models for all API inputs; file type and size validation
- **File Upload:** Extension whitelist, MIME type validation, UUID-based file naming
- **SQL Injection:** Prevented via SQLAlchemy ORM (parameterised queries)
- **Auto-redirect:** Frontend interceptor clears token and redirects to login on 401 responses

---

## Documentation

| Document | Description |
|----------|-------------|
| [API Documentation](docs/api-documentation.md) | Complete API reference |
| [Project Structure](docs/project-structure.md) | Architecture and design overview |
| [Dataset Research](docs/dataset-research-and-selection.md) | Dataset evaluation (5 datasets), selection rationale |
| [EDA Report](docs/data-profiling-eda-report.md) | Data profiling, quality assessment, 15 visualisation summaries |

---

## Legal Notice

This system is designed for **legitimate security research and academic purposes only**. Users must comply with all applicable laws and regulations, respect privacy and data protection requirements, and obtain proper authorisation for any monitoring activities. The developers are not responsible for any misuse of this software.

## License

This project is licensed under the MIT License.

