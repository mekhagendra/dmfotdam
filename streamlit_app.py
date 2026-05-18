"""
Streamlit app for Terrorism Detection & Monitoring (TDM) System.

Provides UI for:
  - File upload (PDF, DOCX, TXT, CSV, XLSX, JSON)
  - Direct text input
  - ML-based threat analysis
  - Result visualization with threat score, level, and key indicators

Models used (loaded from backend/data/models/):
  1. Linear SVC (TF-IDF) - primary fallback
  2. Random Forest - ensemble option
  3. SGD - fast classifier
  4. Sentence-BERT + Logistic Regression - embedding-based
"""

import os
import io
import json
import tempfile
from pathlib import Path
from collections import Counter
from typing import Dict, Tuple, Optional, Any
from dotenv import load_dotenv

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib

# Load environment variables from .env (local dev)
load_dotenv()

# ============================================================================
# Configuration & Secrets Management
# ============================================================================

def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get config from Streamlit secrets, environment, or default."""
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except:
        return os.getenv(key, default)

DEBUG_MODE = get_config("DEBUG", "false").lower() == "true"
MONGODB_URL = get_config("MONGODB_URL")
API_BASE_URL = get_config("API_BASE_URL", "http://localhost:8080")
SEED_ADMIN_USER = get_config("SEED_ADMIN_USER", "admin")

# Page config
st.set_page_config(
    page_title="TDM - Threat Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Styling & Theme
# ============================================================================

st.markdown("""
<style>
    .threat-critical { color: #ff3333; font-weight: bold; }
    .threat-high { color: #ff8800; font-weight: bold; }
    .threat-medium { color: #ffaa00; font-weight: bold; }
    .threat-low { color: #00cc00; font-weight: bold; }
    .metric-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Model Loading & Caching
# ============================================================================

MODEL_DIR = Path(__file__).parent / "backend" / "data" / "models"


@st.cache_resource
def load_linsvc_model() -> Tuple[Any, Any]:
    """Load LinearSVC model and TF-IDF vectorizer."""
    try:
        model_path = MODEL_DIR / "linsvc_threat_model.joblib"
        if not model_path.exists():
            st.warning(f"⚠️ Model not found at {model_path}")
            return None, None
        model_dict = joblib.load(model_path)
        return model_dict.get("model"), model_dict.get("vectorizer")
    except Exception as e:
        st.error(f"Failed to load LinearSVC model: {e}")
        return None, None


@st.cache_resource
def load_rf_model() -> Tuple[Any, Any]:
    """Load Random Forest model and vectorizer."""
    try:
        model_path = MODEL_DIR / "rf_threat_model.joblib"
        if not model_path.exists():
            return None, None
        model_dict = joblib.load(model_path)
        return model_dict.get("model"), model_dict.get("vectorizer")
    except Exception as e:
        st.warning(f"Random Forest not available: {e}")
        return None, None


@st.cache_resource
def load_sgd_model() -> Tuple[Any, Any]:
    """Load SGD model and vectorizer."""
    try:
        model_path = MODEL_DIR / "sgd_threat_model.joblib"
        if not model_path.exists():
            return None, None
        model_dict = joblib.load(model_path)
        return model_dict.get("model"), model_dict.get("vectorizer")
    except Exception as e:
        st.warning(f"SGD model not available: {e}")
        return None, None


@st.cache_resource
def load_sbert_model() -> Tuple[Any, Any]:
    """Load Sentence-BERT + LogReg model and vectorizer."""
    try:
        model_path = MODEL_DIR / "sbert_logreg_model.joblib"
        if not model_path.exists():
            return None, None
        model_dict = joblib.load(model_path)
        return model_dict.get("model"), model_dict.get("vectorizer")
    except Exception as e:
        st.warning(f"Sentence-BERT model not available: {e}")
        return None, None


# ============================================================================
# Text Extraction
# ============================================================================

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF."""
    try:
        from PyPDF2 import PdfReader
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text
    except Exception as e:
        st.warning(f"Error extracting PDF: {e}")
        return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX."""
    try:
        from docx import Document
        docx_file = io.BytesIO(file_bytes)
        doc = Document(docx_file)
        text = "\n".join(p.text for p in doc.paragraphs if p.text)
        return text
    except Exception as e:
        st.warning(f"Error extracting DOCX: {e}")
        return ""


def extract_text_from_csv(file_bytes: bytes) -> str:
    """Extract text from CSV."""
    try:
        csv_file = io.StringIO(file_bytes.decode("utf-8", errors="replace"))
        df = pd.read_csv(csv_file, on_bad_lines="skip", low_memory=False)
        text_cols = df.select_dtypes(include=["object"]).columns.tolist()
        if not text_cols:
            return df.to_string(max_rows=500)
        text = "\n".join(
            " ".join(str(v) for v in row if pd.notna(v))
            for _, row in df[text_cols].head(5000).iterrows()
        )
        return text
    except Exception as e:
        st.warning(f"Error extracting CSV: {e}")
        return ""


def extract_text_from_excel(file_bytes: bytes) -> str:
    """Extract text from XLSX."""
    try:
        excel_file = io.BytesIO(file_bytes)
        df = pd.read_excel(excel_file, engine="openpyxl")
        text_cols = df.select_dtypes(include=["object"]).columns.tolist()
        if not text_cols:
            return df.to_string(max_rows=500)
        text = "\n".join(
            " ".join(str(v) for v in row if pd.notna(v))
            for _, row in df[text_cols].head(5000).iterrows()
        )
        return text
    except Exception as e:
        st.warning(f"Error extracting Excel: {e}")
        return ""


def extract_text_from_json(file_bytes: bytes) -> str:
    """Extract text from JSON."""
    try:
        data = json.loads(file_bytes.decode("utf-8", errors="replace"))
        
        def extract_strings(obj, depth=0, max_depth=5):
            if depth > max_depth:
                return []
            strings = []
            if isinstance(obj, dict):
                for v in obj.values():
                    strings.extend(extract_strings(v, depth + 1, max_depth))
            elif isinstance(obj, list):
                for item in obj:
                    strings.extend(extract_strings(item, depth + 1, max_depth))
            elif isinstance(obj, str):
                strings.append(obj)
            return strings
        
        strings = extract_strings(data)
        return "\n".join(strings)
    except Exception as e:
        st.warning(f"Error extracting JSON: {e}")
        return ""


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Dispatch extraction by file extension."""
    ext = Path(filename).suffix.lower()
    
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext == ".docx":
        return extract_text_from_docx(file_bytes)
    elif ext == ".csv":
        return extract_text_from_csv(file_bytes)
    elif ext in (".xlsx", ".xls"):
        return extract_text_from_excel(file_bytes)
    elif ext == ".json":
        return extract_text_from_json(file_bytes)
    elif ext == ".txt":
        return file_bytes.decode("utf-8", errors="replace")
    else:
        st.error(f"Unsupported file type: {ext}")
        return ""


# ============================================================================
# Threat Analysis
# ============================================================================

THREAT_KEYWORDS = {
    "violence": [
        "attack", "bomb", "explosive", "weapon", "kill", "detonate",
        "shooting", "assassination", "violence", "armed", "militant",
    ],
    "extremism": [
        "radical", "extremist", "extremism", "jihad", "propaganda",
        "ideology", "radicalization", "fanaticism", "zealot",
    ],
    "planning": [
        "plan", "target", "coordinate", "operation", "surveillance",
        "reconnaissance", "schedule", "plot", "scheme",
    ],
    "financing": [
        "funding", "money laundering", "cryptocurrency", "hawala",
        "financial", "sponsor", "bankroll", "fund", "finance",
    ],
}


def extract_keywords(text: str, top_n: int = 5) -> list:
    """Extract top N most frequent tokens from text."""
    try:
        words = text.lower().split()
        # Filter common English stopwords
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "is", "are", "was", "were", "be", "been", "being", "have",
            "has", "had", "do", "does", "did", "will", "would", "could", "should",
        }
        filtered = [w.strip(".,!?;:") for w in words if w and w.lower() not in stopwords]
        counter = Counter(filtered)
        return [word for word, _ in counter.most_common(top_n)]
    except Exception:
        return []


def detect_threat_keywords(text: str) -> Dict[str, list]:
    """Find threat-related keywords in text."""
    text_lower = text.lower()
    found = {}
    for category, keywords in THREAT_KEYWORDS.items():
        found[category] = [kw for kw in keywords if kw in text_lower]
    return {k: v for k, v in found.items() if v}


def classify_with_model(text: str, model: Any, vectorizer: Any) -> Optional[float]:
    """Classify text with a sklearn model."""
    try:
        if model is None or vectorizer is None:
            return None
        text_vec = vectorizer.transform([text])
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(text_vec)[0]
            # Return probability of threat class (usually class 1)
            return float(proba[-1]) if len(proba) > 1 else None
        else:
            pred = model.predict(text_vec)[0]
            return float(pred)
    except Exception as e:
        st.warning(f"Classification error: {e}")
        return None


def compute_threat_score(text: str, model_proba: Optional[float]) -> Tuple[float, str]:
    """
    Compute hybrid threat score (70% ML + 30% rule-based).
    
    Returns:
        (score, level) where score is 0-1 and level is 'low', 'medium', 'high', 'critical'
    """
    ml_score = model_proba if model_proba is not None else 0.5
    
    # Rule-based keyword score
    threat_kw = detect_threat_keywords(text)
    kw_count = sum(len(v) for v in threat_kw.values())
    kw_score = min(1.0, kw_count / 10.0)  # Normalize to 0-1
    
    # Blend: 70% ML + 30% rule-based
    final_score = 0.70 * ml_score + 0.30 * kw_score
    
    # Map to threat level
    if final_score >= 0.76:
        level = "🔴 Critical"
    elif final_score >= 0.51:
        level = "🟠 High"
    elif final_score >= 0.26:
        level = "🟡 Medium"
    else:
        level = "🟢 Low"
    
    return final_score, level


# ============================================================================
# UI & Main App
# ============================================================================

def main():
    st.title("🛡️ Terrorism Detection & Monitoring System")
    st.markdown(
        "Analyze documents and text for potential extremism-related threats using ML-powered classification."
    )
    
    # Load models
    with st.spinner("Loading models..."):
        linsvc_model, linsvc_vec = load_linsvc_model()
        rf_model, rf_vec = load_rf_model()
        sgd_model, sgd_vec = load_sgd_model()
        sbert_model, sbert_vec = load_sbert_model()
    
    if linsvc_model is None:
        st.error("❌ No models found. Please ensure backend/data/models/ contains trained models.")
        st.stop()
    
    st.success("✅ Models loaded successfully")
    
    # Show connection status
    if MONGODB_URL:
        st.info("💾 Connected to MongoDB")
    else:
        st.warning("⚠️ MongoDB not configured — analysis will work, but no persistence") if DEBUG_MODE else None
    
    # Sidebar controls
    st.sidebar.header("⚙️ Settings")
    model_choice = st.sidebar.selectbox(
        "Select Classification Model",
        [
            "Linear SVC (Default)",
            "Random Forest",
            "SGD (Fast)",
            "Sentence-BERT (Semantic)",
            "Ensemble (Average all)",
        ]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**About**: This system blends ML classification (70%) with rule-based keyword detection (30%) to identify threats."
    )
    
    # Debug info
    if DEBUG_MODE:
        with st.sidebar.expander("🐛 Debug Info"):
            st.write(f"**MongoDB**: {'✅ Configured' if MONGODB_URL else '❌ Not configured'}")
            st.write(f"**API Base URL**: {API_BASE_URL}")
            st.write(f"**Model Dir**: {MODEL_DIR}")
    
    # Input tab selection
    tab1, tab2 = st.tabs(["📤 Upload File", "📝 Paste Text"])
    
    text_input = ""
    
    with tab1:
        st.markdown("### Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a file (PDF, DOCX, TXT, CSV, XLSX, JSON)",
            type=["pdf", "docx", "txt", "csv", "xlsx", "xls", "json"]
        )
        
        if uploaded_file is not None:
            st.info(f"📎 File: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
            file_bytes = uploaded_file.read()
            text_input = extract_text_from_file(file_bytes, uploaded_file.name)
            
            if text_input:
                st.success(f"✅ Extracted {len(text_input)} characters")
                with st.expander("📖 Preview extracted text"):
                    st.text_area("", text_input[:1000] + "..." if len(text_input) > 1000 else text_input, height=200, disabled=True)
            else:
                st.warning("⚠️ No text could be extracted from file.")
    
    with tab2:
        st.markdown("### Paste Text Directly")
        text_input = st.text_area(
            "Enter or paste text to analyze:",
            height=250,
            placeholder="Paste text here..."
        )
    
    # Analysis section
    st.markdown("---")
    
    if text_input.strip():
        st.markdown("### 🔍 Analysis Results")
        
        # Classify with selected model(s)
        results = {}
        
        if model_choice == "Linear SVC (Default)":
            prob = classify_with_model(text_input, linsvc_model, linsvc_vec)
            results["Linear SVC"] = prob
        elif model_choice == "Random Forest":
            prob = classify_with_model(text_input, rf_model, rf_vec)
            results["Random Forest"] = prob
        elif model_choice == "SGD (Fast)":
            prob = classify_with_model(text_input, sgd_model, sgd_vec)
            results["SGD"] = prob
        elif model_choice == "Sentence-BERT (Semantic)":
            prob = classify_with_model(text_input, sbert_model, sbert_vec)
            results["Sentence-BERT"] = prob
        elif model_choice == "Ensemble (Average all)":
            all_probs = []
            for model, vec, name in [
                (linsvc_model, linsvc_vec, "Linear SVC"),
                (rf_model, rf_vec, "Random Forest"),
                (sgd_model, sgd_vec, "SGD"),
                (sbert_model, sbert_vec, "Sentence-BERT"),
            ]:
                prob = classify_with_model(text_input, model, vec)
                if prob is not None:
                    all_probs.append(prob)
                    results[name] = prob
            if all_probs:
                results["Ensemble"] = np.mean(all_probs)
        
        # Get final score
        model_proba = results.get(model_choice, None) or results.get("Ensemble", None)
        threat_score, threat_level = compute_threat_score(text_input, model_proba)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🎯 Threat Score", f"{threat_score:.2%}")
        
        with col2:
            st.metric("📊 Threat Level", threat_level)
        
        with col3:
            st.metric("📏 Text Length", f"{len(text_input):,} chars")
        
        with col4:
            keywords = extract_keywords(text_input, top_n=1)
            st.metric("🔑 Top Keyword", keywords[0] if keywords else "N/A")
        
        # Model scores
        if len(results) > 1:
            st.markdown("#### 📈 Model Scores")
            scores_df = pd.DataFrame(
                list(results.items()),
                columns=["Model", "Threat Probability"]
            )
            scores_df["Threat Probability"] = scores_df["Threat Probability"].apply(lambda x: f"{x:.2%}")
            st.dataframe(scores_df, use_container_width=True, hide_index=True)
        
        # Threat indicators
        threat_kw = detect_threat_keywords(text_input)
        if threat_kw:
            st.markdown("#### 🚨 Detected Threat Keywords")
            for category, keywords in threat_kw.items():
                st.info(f"**{category.title()}**: {', '.join(keywords)}")
        else:
            st.success("✅ No explicit threat keywords detected.")
        
        # Key terms
        top_keywords = extract_keywords(text_input, top_n=10)
        if top_keywords:
            st.markdown("#### 🔑 Top Terms in Document")
            st.write(", ".join(top_keywords))
        
        # Recommendations
        st.markdown("#### 📋 Recommendations")
        if threat_score >= 0.76:
            st.error("🔴 **CRITICAL**: Immediate review and escalation recommended.")
        elif threat_score >= 0.51:
            st.warning("🟠 **HIGH**: Document requires detailed analysis.")
        elif threat_score >= 0.26:
            st.info("🟡 **MEDIUM**: Monitor for context and patterns.")
        else:
            st.success("🟢 **LOW**: No immediate threat indicators detected.")
    
    else:
        st.info("👆 Upload a file or paste text to begin analysis.")


if __name__ == "__main__":
    main()
