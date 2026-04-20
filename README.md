# Digital Media Forensics on Terrorism Detection and Monitoring (DMFOTDAM)

A full-stack web data mining application that uses **machine learning**, **deep learning (BERT)**, and **natural language processing** to detect and classify potential extremism-related threats from uploaded documents, structured data files, and free-form text.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
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

The DMFOTDAM System analyzes text from multiple file formats (PDF, DOCX, TXT, CSV, Excel, JSON) and classifies content using a **multi-layered hybrid approach** that combines:

1. **Rule-based keyword detection** across four threat categories (violence, extremism, planning, financing)
2. **Traditional ML classifiers** — TF-IDF + Linear SVC, Logistic Regression, Random Forest, SGD (trained on 2,776 extremism-labelled messages)
3. **Deep learning (BERT)** — Fine-tuned DistilBERT and BERT-base transformer models
4. **NLP embedding models** — Sentence-BERT embeddings with Logistic Regression and XGBoost classifiers

The system prefers the **DistilBERT model** when available (85.6% F1-score, 92.6% ROC-AUC), falling back to the TF-IDF + Linear SVC model (83.6% F1). The final threat score blends ML output with rule-based analysis: **70% ML + 30% rule-based**, classifying content as **low** or **high** threat.

---

## How It Works

This section explains **what happens** when a user uploads a document or pastes text, **which models** are involved, **how each model works**, and **why** we chose them.

### The Big Picture: From Text to Threat Score

```
  User uploads a document or types text
                    │
                    ▼
       ┌────────────────────────┐
       │  1. TEXT EXTRACTION    │   Extract readable text from PDF, DOCX,
       │     (File Handler)     │   CSV, Excel, JSON, or plain text
       └────────────────────────┘
                    │
                    ▼
       ┌────────────────────────┐
       │  2. RULE-BASED SCAN   │   Search for known threat keywords
       │     (Keyword Engine)   │   across 4 categories (30% of score)
       └────────────────────────┘
                    │
                    ▼
       ┌────────────────────────┐
       │  3. ML CLASSIFICATION  │   Feed text into trained ML model
       │     (BERT or TF-IDF)   │   to predict threat level (70% of score)
       └────────────────────────┘
                    │
                    ▼
       ┌────────────────────────┐
       │  4. SCORE BLENDING     │   Combine: 70% ML + 30% Rule-based
       │     (Hybrid Score)     │   → Final threat level: low or high
       └────────────────────────┘
                    │
                    ▼
         Dashboard shows results
         with threat level, score,
         keywords, and details
```

### Step 1: Text Extraction

The system accepts **7 file formats**. Each file is parsed into plain text before analysis:

| Format | How it's extracted |
|--------|--------------------|
| **TXT** | Read directly |
| **PDF** | Each page is extracted using PyPDF2 |
| **DOCX** | Paragraphs are extracted using python-docx |
| **CSV** | All text columns are concatenated row-by-row |
| **Excel** | Same as CSV, using openpyxl engine |
| **JSON** | All string values are recursively extracted |

For **structured data** files (CSV, Excel, JSON), the system additionally performs **data profiling** — statistics on rows, columns, missing values, numeric distributions, and top categorical values — alongside the threat analysis.

### Step 2: Rule-Based Keyword Detection

Before any ML model runs, the system scans the text for **known threat-related words** organised into four categories:

| Category | Example Keywords | What it detects |
|----------|-----------------|-----------------|
| **Violence** | attack, bomb, explosive, weapon, kill, detonate | Direct references to physical violence or weapons |
| **Extremism** | radical, extremist, militant, jihad, propaganda | Ideological extremism or radicalisation language |
| **Planning** | plan, target, coordinate, operation, surveillance | Operational planning or reconnaissance activity |
| **Financing** | funding, money laundering, cryptocurrency, hawala | Terrorism financing or illicit money flows |

**How the rule-based score works:**
- Count how many threat keywords appear and how often
- Calculate **keyword density** (threat words ÷ total words)
- Award bonus points for **category diversity** (threats across multiple categories are scored higher)
- Convert to a 0–1 score and map to a threat level

> **Why include rule-based?** ML models can occasionally misclassify edge cases. The keyword layer acts as a safety net — if text explicitly mentions "bomb" or "attack", the rule-based component ensures the threat score reflects that, even if the ML model is uncertain.

### Step 3: Machine Learning Classification

This is the core intelligence layer. The system supports **four different model families**, each with distinct strengths:

---

#### Model A: DistilBERT (Primary Model — Best Performance)

| Property | Value |
|----------|-------|
| **Type** | Deep learning transformer (fine-tuned) |
| **Base model** | `distilbert-base-uncased` from HuggingFace |
| **Test F1-score** | **85.62%** |
| **Test accuracy** | **85.61%** |
| **ROC-AUC** | **92.63%** |
| **Training** | 4 epochs, batch size 16, learning rate 2e-5 |

**How it works (simplified):**
1. The input text is split into small pieces called **tokens** (words or parts of words)
2. Each token is converted into a numerical **embedding** — a list of 768 numbers that captures the token's meaning
3. The tokens pass through **6 transformer layers**, where each token "pays attention" to every other token. This is the key innovation — the model understands that "bomb" after "cherry" is very different from "bomb" after "car"
4. The final representation of the entire text is fed into a **classification head** (a small neural network) that outputs two probabilities: P(extremist) and P(non-extremist)
5. The class with the higher probability becomes the prediction

**What is a Transformer?**
Think of it like a very sophisticated reader. A traditional model reads word by word, left to right. A transformer reads **all words simultaneously** and figures out which words are most relevant to each other. When it sees "The suspect planned to detonate the device at the embassy", it connects "suspect" ↔ "planned" ↔ "detonate" ↔ "device" ↔ "embassy" all at once, understanding the full context.

**What is "Fine-tuning"?**
DistilBERT was **pre-trained by Google** on billions of English sentences (Wikipedia + books). It already understands English grammar, word meanings, and context. We then **fine-tuned** it — we showed it our 2,776 extremism-labelled messages and adjusted its parameters so it specialises in distinguishing extremist from non-extremist text. This is like hiring an English literature expert and training them specifically for security analysis.

**Why DistilBERT over full BERT?**
- DistilBERT is a **compressed version** of BERT — 40% smaller and 60% faster, with only a 3% drop in accuracy
- On our dataset, DistilBERT actually **outperformed** full BERT (85.6% vs 83.1% F1) — likely because the smaller model is less prone to overfitting on our relatively small dataset
- Faster inference means quicker analysis for users

---

#### Model B: BERT-base (Alternative Deep Learning Model)

| Property | Value |
|----------|-------|
| **Type** | Deep learning transformer (fine-tuned) |
| **Base model** | `bert-base-uncased` from HuggingFace |
| **Test F1-score** | **83.10%** |
| **Test accuracy** | **83.09%** |
| **ROC-AUC** | **91.51%** |
| **Training** | 4 epochs, batch size 16, learning rate 2e-5 |

BERT-base is the **full-size** version with 12 transformer layers (vs 6 in DistilBERT) and 110M parameters (vs 66M). It works identically to DistilBERT but with more capacity. On our dataset, it slightly underperformed DistilBERT, suggesting the extra capacity led to mild **overfitting** on our 2,776-sample dataset. However, with a larger dataset, BERT-base would likely surpass DistilBERT.

---

#### Model C: TF-IDF + Linear SVC (Fallback Model)

| Property | Value |
|----------|-------|
| **Type** | Traditional ML (statistical) |
| **Vectoriser** | TF-IDF (30,000 features, unigrams + bigrams) |
| **Classifier** | Linear Support Vector Classifier (SVC) |
| **Test F1-score** | **83.64%** |
| **Test accuracy** | **83.63%** |
| **CV F1 (5-fold)** | 82.52% ± 1.52% |

**How it works (simplified):**
1. **TF-IDF Vectorisation** — converts each text into a vector of 30,000 numbers. Each number represents how important a particular word (or pair of words) is to that text, compared to all other texts in the training set. "TF" (Term Frequency) measures how often a word appears in the text; "IDF" (Inverse Document Frequency) downweights common words like "the", "is", "and"
2. **Linear SVC** — draws a straight line (actually a hyperplane in 30,000-dimensional space) that best separates "extremist" texts from "non-extremist" texts. New text is placed in this space, and whichever side of the line it falls on determines its classification

**Why include this model?**
- It runs on **any machine** without GPU or PyTorch — ideal as a fallback
- Training takes **seconds** instead of minutes
- It's interpretable: you can see exactly which words influenced the decision
- Performance is surprisingly close to BERT (only 2% behind)

**Other classifiers tested (all with TF-IDF):**

| Classifier | CV F1 | Notes |
|-----------|-------|-------|
| Linear SVC | 82.52% | **Best traditional model** — selected as the fallback |
| Logistic Regression | 82.20% | Very close to SVC, slightly simpler |
| Random Forest (300 trees) | 82.06% | Good but slower, less suited for sparse text data |
| SGD (Modified Huber) | 81.05% | Fastest training, good for very large datasets |

---

#### Model D: Sentence-BERT + Logistic Regression (Embedding Model)

| Property | Value |
|----------|-------|
| **Type** | Neural embeddings + traditional classifier |
| **Embedding model** | `all-MiniLM-L6-v2` (Sentence-BERT) |
| **Classifier** | Logistic Regression |
| **Saved as** | `sbert_logreg_model.joblib` |

**How it works (simplified):**
1. **Sentence-BERT** reads the entire text and produces a single vector of **384 numbers** that captures the overall meaning of the text. Unlike TF-IDF (which just counts words), this vector understands that "the suspect detonated an explosive" and "a bomb was set off by the attacker" have **similar meanings** even though they share almost no words
2. **Logistic Regression** uses this 384-number representation to classify the text as extremist or non-extremist

**Why this approach?**
- It's a middle ground between TF-IDF (fast but shallow) and full BERT fine-tuning (powerful but resource-intensive)
- The Sentence-BERT embeddings capture **semantic meaning**, not just word frequency
- The classifier is very fast — the heavy lifting happens only once during encoding

---

### Step 4: Hybrid Score Blending

The final threat score that users see is a **weighted combination** of ML and rule-based analysis:

```
final_score = 0.70 × ML_model_score + 0.30 × rule_based_score
```

| Component | Weight | Why |
|-----------|--------|-----|
| ML model (BERT or TF-IDF) | **70%** | The ML model captures subtle language patterns that keyword lists miss — it understands context, not just individual words |
| Rule-based keywords | **30%** | The keyword layer ensures that explicit threat language is never overlooked, even if the ML model is uncertain |

**Score → Threat Level Mapping:**

| Score Range | Threat Level | Action |
|-------------|-------------|--------|
| 0.00 – 0.25 | **Low** | No immediate concern |
| 0.26 – 0.50 | **Medium** | Worth monitoring |
| 0.51 – 0.75 | **High** | Requires attention |
| 0.76 – 1.00 | **Critical** | Immediate review needed |

### Model Selection at Runtime

The system automatically selects the best available model:

```
                  ┌─────────────────────────┐
                  │  Is BERT model loaded?   │
                  └─────────┬───────────────┘
                       yes  │  no
                       ▼    │   ▼
              ┌──────────┐  │  ┌──────────────────────┐
              │ Use BERT │  │  │ Is sklearn model      │
              │ (85.6%)  │  │  │ loaded?               │
              └──────────┘  │  └───────┬──────────────┘
                            │     yes  │  no
                            │     ▼    │   ▼
                            │  ┌──────────┐  ┌───────────────┐
                            │  │ Use SVC  │  │ Rule-based    │
                            │  │ (83.6%)  │  │ only          │
                            │  └──────────┘  └───────────────┘
```

### Why Multiple Models? A Summary

| Model | Strength | Weakness | Best for |
|-------|----------|----------|----------|
| **DistilBERT** | Understands context and meaning; highest accuracy | Requires PyTorch (~500MB); slower inference | Production use with adequate hardware |
| **TF-IDF + SVC** | Fast, lightweight, interpretable | Misses context ("car bomb" vs "cherry bomb") | Lightweight deployments, fallback |
| **SBERT + LogReg** | Semantic understanding without fine-tuning | Depends on pre-trained embeddings | Quick experimentation, ensemble |
| **Rule-based** | Transparent, no training needed, catches explicit threats | Cannot understand context or paraphrasing | Supplementary safety net |

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Document Upload & Analysis** | Upload PDF, DOCX, TXT, CSV, Excel, JSON files for automated threat analysis |
| **Text Analysis** | Paste and analyze free-form text directly via API or the web interface |
| **ML-Powered Classification** | Multiple models: DistilBERT (85.6% F1), TF-IDF + Linear SVC (83.6% F1), SBERT + LogReg, SBERT + XGBoost |
| **Data Profiling** | Structured data files (CSV/Excel/JSON) receive full statistical profiling alongside threat analysis |
| **Interactive Dashboard** | Real-time charts, threat distribution, and analytics via Chart.js and Recharts |
| **Live Monitoring** | Configurable web source monitoring with keyword-based alerting |
| **Alert System** | Automated alert generation with threat level, source tracking, and resolution workflow |
| **User Authentication** | JWT-based authentication with role-based access (admin / analyst / viewer) |
| **Reporting** | Browse, filter, and review all historical analysis results |

---

## Architecture

```
┌──────────────────┐     ┌────────────────────┐     ┌──────────────────────────────┐
│  React Frontend  │────▶│   FastAPI Backend   │────▶│  ML / NLP / DL Engine        │
│  (TypeScript +   │     │   (REST API)        │     │                              │
│   Tailwind CSS)  │     │                     │     │  ┌─ BERT (DistilBERT)  ◀── preferred
└──────────────────┘     └────────────────────┘     │  ├─ SBERT + LogReg / XGBoost
         │                         │                │  └─ Rule-based keywords
         ▼                         ▼                └──────────────────────────────┘
┌──────────────────┐     ┌────────────────────┐                  │
│  Web Browser     │     │  SQLite / Postgres  │                  ▼
│  localhost:3000  │     │  (SQLAlchemy ORM)   │     ┌──────────────────────────────┐
└──────────────────┘     └────────────────────┘     │  Trained Models              │
                                                    │  bert_threat_model/          │
                                                    │  sbert_logreg_model.joblib   │
                                                    └──────────────────────────────┘
```

---

## Technology Stack

### Backend (Python 3.11+)

| Component | Technology |
|-----------|-----------|
| Web Framework | FastAPI 0.104 + Uvicorn |
| ORM / Database | SQLAlchemy 2.0 (async) + aiosqlite (dev) / asyncpg (prod) |
| Machine Learning | scikit-learn (TF-IDF + SVC/SGD/LR/RF), joblib |
| Deep Learning | PyTorch, HuggingFace Transformers (DistilBERT, BERT-base) |
| NLP Embeddings | sentence-transformers (all-MiniLM-L6-v2), spaCy, XGBoost |
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
│   │   │   ├── ml_service.py          # Loads BERT (preferred) or sklearn models for inference
│   │   │   ├── web_scraper.py         # URL content scraping
│   │   │   └── live_monitor.py        # Background monitoring service
│   │   └── utils/
│   │       ├── file_handler.py        # File validation, save, delete
│   │       ├── text_processor.py      # Text cleaning utilities
│   │       └── validators.py          # Input validation helpers
│   ├── data/
│   │   ├── datasets/
│   │   │   ├── extremisim.csv         # Extremism dataset (2,776 labelled messages)
│   │   │   └── eda_output/            # 20 EDA + model visualisation PNGs
│   │   ├── models/
│   │   │   ├── bert_threat_model/            # Fine-tuned DistilBERT model + tokenizer
│   │   │   ├── sbert_logreg_model.joblib     # SBERT embeddings + Logistic Regression
│   │   │   └── bert_training_summary.json    # BERT training results
│   │   └── uploads/                   # User-uploaded files
│   ├── scripts/
│   │   ├── train_models.py            # TF-IDF + classical ML training (SVC, LR, RF, SGD)
│   │   ├── train_bert_model.py        # BERT / DistilBERT fine-tuning
│   │   ├── train_nlp_models.py        # SBERT + LogReg/XGBoost, spaCy training
│   │   └── run_eda.py                 # Exploratory data analysis + visualisations
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

The **Extremism Message Dataset** — 2,776 labelled messages classified as `EXTREMIST` or `NON_EXTREMIST`. Each row contains an `Original_Message` (text) and an `Extremism_Label`.

### Models Trained

| Model | Type | Test F1 | Test Accuracy | ROC-AUC | Training Script |
|-------|------|---------|---------------|---------|-----------------|
| **DistilBERT** | Transformer (fine-tuned) | **85.62%** | 85.61% | 92.63% | `train_bert_model.py` |
| **BERT-base** | Transformer (fine-tuned) | 83.10% | 83.09% | 91.51% | `train_bert_model.py` |
| **TF-IDF + Linear SVC** | Traditional ML | 83.64% | 83.63% | — | `train_models.py` |
| **TF-IDF + Logistic Regression** | Traditional ML | 82.20% (CV) | 82.21% (CV) | — | `train_models.py` |
| **TF-IDF + Random Forest** | Traditional ML | 82.06% (CV) | 82.06% (CV) | — | `train_models.py` |
| **TF-IDF + SGD** | Traditional ML | 81.05% (CV) | 81.05% (CV) | — | `train_models.py` |
| **SBERT + Logistic Regression** | Embedding + ML | trained | saved | — | `train_nlp_models.py` |
| **SBERT + XGBoost** | Embedding + ML | trained | saved | — | `train_nlp_models.py` |

### Pipeline Architecture (TF-IDF Models)

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
│  Linear SVC (best)           │
│  - Balanced class weights    │
│  - CalibratedClassifierCV    │
│  - Probability estimates     │
└──────────────────────────────┘
    │
    ▼
Prediction + Probabilities
```

### Pipeline Architecture (BERT Models)

```
Input Text
    │
    ▼
┌──────────────────────────────┐
│  BERT Tokeniser              │
│  - WordPiece tokenisation    │
│  - Max length: 128 tokens    │
│  - Padding + truncation      │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│  DistilBERT / BERT-base      │
│  - 6 / 12 transformer layers │
│  - Self-attention mechanism   │
│  - 66M / 110M parameters     │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│  Classification Head          │
│  - Linear layer (768 → 2)    │
│  - Softmax probabilities     │
└──────────────────────────────┘
    │
    ▼
Prediction: low / high + probabilities
```

### Hybrid Scoring

The final threat score combines ML and rule-based methods:

```
threat_score = 0.7 × ML_score + 0.3 × rule_based_score
```

The rule-based component uses keyword density and category diversity across four threat categories (violence, extremism, planning, financing).

### Training the Models

```bash
cd backend
source venv/bin/activate

# Train traditional ML models (TF-IDF + classifiers) — runs in seconds
python scripts/train_models.py

# Train BERT models (DistilBERT + BERT-base) — ~15-30 min on CPU, ~5 min on GPU/MPS
python scripts/train_bert_model.py

# Train NLP embedding models (SBERT + LogReg/XGBoost, spaCy)
python scripts/train_nlp_models.py
```

### Visualisations Generated

| # | Chart | Script |
|---|-------|--------|
| 13 | TF-IDF model comparison (4 classifiers) | `train_models.py` |
| 14 | TF-IDF confusion matrix (best model) | `train_models.py` |
| 15 | TF-IDF classification report heatmap | `train_models.py` |
| 16 | BERT training loss curve | `train_bert_model.py` |
| 17 | BERT confusion matrix | `train_bert_model.py` |
| 18 | BERT classification report heatmap | `train_bert_model.py` |
| 19 | BERT model comparison (DistilBERT vs BERT) | `train_bert_model.py` |
| 20 | NLP model comparison (all models) | `train_nlp_models.py` |

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

# Train BERT models (optional, improves accuracy — requires torch)
python scripts/train_bert_model.py

# Train NLP models (optional — requires sentence-transformers)
python scripts/train_nlp_models.py

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

### Reddit Real-Time Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reddit/status` | API status and stored post count |
| POST | `/reddit/scan` | Trigger manual scan (subreddits, limit, threshold) |
| POST | `/reddit/search` | Search Reddit with threat analysis |
| GET | `/reddit/posts` | List flagged posts (filter by threat_level, subreddit, days) |
| GET | `/reddit/posts/{id}` | Get detailed post analysis |
| PATCH | `/reddit/posts/{id}/review` | Mark a post as reviewed |
| GET | `/reddit/trends` | Daily trend data (post volume, avg/max threat scores) |
| GET | `/reddit/subreddits` | Per-subreddit statistics |

**Setup:** Create a Reddit app at https://www.reddit.com/prefs/apps (script type) and set environment variables:

```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT="DMFOTDAM/1.0"
```

The system automatically scans monitored subreddits every 24 hours (configurable via `REDDIT_SCAN_INTERVAL_HOURS`). Each post is analysed by the ML pipeline (BERT/TF-IDF) and flagged if the threat score exceeds the threshold. Results are viewable on the **Trends** and **Extremism Content** frontend pages.

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

### Extremism Message Dataset

- **Source:** Extremism-labelled text messages
- **Records:** 2,776 messages (after cleaning)
- **Columns:** `Original_Message` (text), `Extremism_Label` (`EXTREMIST` / `NON_EXTREMIST`)
- **Label mapping:** `EXTREMIST` → high, `NON_EXTREMIST` → low
- **Train/test split:** 80% / 20% (stratified, 2,220 train / 556 test)

### Exploratory Data Analysis

20 visualisations generated by training scripts and saved to `data/datasets/eda_output/`:

| # | Visualisation | Source |
|---|---------------|--------|
| 01 | Class distribution | `run_eda.py` |
| 02 | Message length distribution | `run_eda.py` |
| 03 | Top n-grams | `run_eda.py` |
| 04 | Correlation heatmap | `run_eda.py` |
| 05 | Average word length | `run_eda.py` |
| 06 | Vocabulary richness | `run_eda.py` |
| 07 | KDE density plot | `run_eda.py` |
| 08 | Feature comparison | `run_eda.py` |
| 09 | Outlier analysis | `run_eda.py` |
| 10 | Punctuation analysis | `run_eda.py` |
| 11 | Term frequency | `run_eda.py` |
| 12 | Data quality | `run_eda.py` |
| 13 | TF-IDF model comparison (4 classifiers) | `train_models.py` |
| 14 | TF-IDF confusion matrix | `train_models.py` |
| 15 | TF-IDF classification report heatmap | `train_models.py` |
| 16 | BERT training loss curve | `train_bert_model.py` |
| 17 | BERT confusion matrix | `train_bert_model.py` |
| 18 | BERT classification report heatmap | `train_bert_model.py` |
| 19 | BERT model comparison (DistilBERT vs BERT) | `train_bert_model.py` |
| 20 | NLP model comparison (all models) | `train_nlp_models.py` |

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

