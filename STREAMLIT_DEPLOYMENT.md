# Streamlit Deployment Guide

This document explains how to deploy the TDM Threat Detection System to **Streamlit Cloud** (streamlit.app).

## Prerequisites

- GitHub account
- Streamlit Cloud account (free at https://streamlit.io/cloud)
- Trained models in `backend/data/models/` committed to git

## Step 1: Prepare the Repository

Ensure your trained models are committed to git:

```bash
git add backend/data/models/*.joblib
git commit -m "Add trained ML models for Streamlit deployment"
git push origin main
```

## Step 2: Create `streamlit_app.py` & Dependencies

✅ Already done! You have:
- `streamlit_app.py` — main Streamlit app
- `requirements-streamlit.txt` — dependencies
- `.streamlit/config.toml` — configuration

## Step 3: Deploy to Streamlit Cloud

### Option A: Simple Deployment (GitHub-connected)

1. **Go to Streamlit Cloud** → https://share.streamlit.io
2. **Sign in** with your GitHub account
3. **Click "New app"**
4. Select:
   - **Repository**: `mekhagendra/dmfotdam` (or your repo)
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
5. Click **Deploy**

Streamlit Cloud will:
- Clone your repo
- Install dependencies from `requirements.txt`
- Run the app
- Assign you a public URL (e.g., `https://yourusername-dmfotdam.streamlit.app/`)

### Option B: Manual Deployment (if git connection fails)

If GitHub connection doesn't work, deploy directly:

```bash
streamlit run streamlit_app.py --logger.level=debug
```

This runs locally on `http://localhost:8501`

## Step 4: Configure Streamlit Cloud (if needed)

After deployment, you can configure secrets and settings in Streamlit Cloud:

1. Go to your app dashboard
2. Click **Settings** → **Secrets**
3. Add any environment variables (optional)

### Example `.streamlit/secrets.toml` (optional):
```toml
# Not needed for basic operation, but useful for production
[database]
url = "your-connection-string"
```

## Step 5: Monitor & Update

- **View logs**: Click "Manage app" → "Logs"
- **Redeploy**: Push changes to `main` branch — Streamlit auto-redeploys
- **Troubleshoot**: Check app logs for model loading errors

---

## Troubleshooting

### ❌ Error: "ModuleNotFoundError: No module named 'joblib'"

**Fix**: Ensure `joblib` is in `requirements-streamlit.txt` (it is).

### ❌ Error: "FileNotFoundError: backend/data/models/*.joblib"

**Issue**: Models not committed to git.

**Fix**:
```bash
git add backend/data/models/
git commit -m "Add trained models"
git push origin main
```

Then redeploy on Streamlit Cloud.

### ❌ Slow app startup

**Reason**: Models are large. Streamlit caches them with `@st.cache_resource`, so 2nd+ load is instant.

**Tip**: Consider uploading models to a cloud storage (AWS S3, Google Cloud) for faster downloads.

### ❌ Memory exceeded on Streamlit Cloud

**Solution**: 
- Streamlit Cloud provides 1 GB RAM free tier
- If models exceed limit, consider deploying to:
  - **Render** (https://render.com) — Free tier, 512MB RAM
  - **Railway** (https://railway.app) — $5/month, 1GB RAM
  - **Azure Container Apps** — Pay-per-use

---

## Features Included

✅ **File Upload** → PDF, DOCX, TXT, CSV, XLSX, JSON extraction  
✅ **Text Input** → Paste text directly  
✅ **Multi-Model Classification** → Linear SVC, Random Forest, SGD, Sentence-BERT, Ensemble  
✅ **Hybrid Scoring** → 70% ML + 30% rule-based keywords  
✅ **Threat Indicators** → Keyword detection, threat levels  
✅ **Real-time Analysis** → Instant results  

---

## Production Deployment (Advanced)

For production use beyond Streamlit Cloud's free tier:

### Option: Docker + Cloud Run (Google Cloud)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements-streamlit.txt .
RUN pip install -r requirements-streamlit.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501"]
```

Deploy to Google Cloud Run:
```bash
gcloud run deploy tdm-streamlit --source . --platform managed --region us-central1
```

### Option: Use FastAPI + Streamlit Together

If you need the full backend (MongoDB, schedulers, user management):

1. Deploy FastAPI to Render or Railway
2. Deploy Streamlit to Streamlit Cloud
3. Streamlit calls FastAPI API endpoints

See `ARCHITECTURE.md` for full integration.

---

## Local Testing Before Deploy

Test the Streamlit app locally:

```bash
cd /Users/khagendraneupane/Development/education/TDM
streamlit run streamlit_app.py
```

Then open http://localhost:8501 and test file upload + analysis.

---

## Environment Variables & Secrets

### Local Development (`.env` file)

Create a `.env` file in the project root:

```bash
# .env
DEBUG=true
MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/tdm
API_BASE_URL=http://localhost:8080
SEED_ADMIN_USER=admin
```

The app automatically loads `.env` using `python-dotenv`.

### Local Secrets (`.streamlit/secrets.toml`)

For local testing with Streamlit secrets:

```toml
# .streamlit/secrets.toml (never commit this!)
[app]
debug = true

[database]
url = "mongodb+srv://user:password@cluster.mongodb.net/tdm"

[api]
base_url = "http://localhost:8080"
```

Access in code:
```python
DEBUG = get_config("DEBUG", "false").lower() == "true"
MONGODB_URL = get_config("MONGODB_URL")
```

### Streamlit Cloud Secrets

After deploying to Streamlit Cloud:

1. Go to your app dashboard
2. Click **Manage app** (top right)
3. Click **Secrets** tab
4. Paste your secrets (TOML format):
```toml
[database]
url = "mongodb+srv://username:password@cluster.mongodb.net/tdm"

[api]
base_url = "https://your-api.herokuapp.com"

[app]
debug = false
```
5. Click **Save**

Streamlit Cloud will restart the app and load the secrets.

---

## Next Steps

- ✅ Deploy to Streamlit Cloud
- 🔲 Test with sample files
- 🔲 Share the public URL with stakeholders
- 🔲 Monitor app usage in Streamlit dashboard
- 🔲 (Optional) Add more models or features

---

**Questions?** See Streamlit docs: https://docs.streamlit.io
