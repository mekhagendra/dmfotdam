"""
ML service — pretrained HuggingFace classifier for extremist / harmful content.

Design notes:

* The primary model (HF_MODEL_NAME, default GroNLP/hateBERT) and a fallback
  model (HF_FALLBACK_MODEL_NAME, default cardiffnlp/twitter-roberta-base-hate)
  are loaded lazily. The fallback is loaded in a background thread after the
  primary is ready, so the API is available as soon as the primary finishes.
* When both models are available an ensemble score is computed:
      final = 0.65 * primary + 0.35 * fallback
* SHAP explainability is optional — if the `shap` package is installed,
  `explain_prediction()` returns token-level attribution scores.

Output shape (both success + unavailable):
    {
        "method": "hf_pipeline" | "unavailable",
        "model": "<model name>",
        "threat_score": 0.0..1.0,
        "threat_level": "low|medium|high|critical",
        "label_scores": {label: score, ...},
        "top_label": "<str>",
        "ensemble": true|false,
        "models_used": ["<primary>", "<fallback>"],
        "error": "<str>"   # only when unavailable
    }
"""

from __future__ import annotations

import asyncio
import os
import threading
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_settings = get_settings()

# Module-level variables updated when the pipeline loads successfully.
ACTIVE_MODEL_NAME: str = ""
ACTIVE_MODEL_F1: float = 0.0


# ---------------------------------------------------------------------------
# Lazy singletons — primary + fallback
# ---------------------------------------------------------------------------


class _ModelHolder:
    pipe = None
    error: Optional[str] = None
    lock = threading.Lock()


class _FallbackModelHolder:
    pipe = None
    error: Optional[str] = None
    lock = threading.Lock()


class _SGDModelHolder:
    pipe = None
    error: Optional[str] = None
    lock = threading.Lock()


class _RFModelHolder:
    pipe = None
    error: Optional[str] = None
    lock = threading.Lock()


class _LinSVCModelHolder:
    pipe = None
    error: Optional[str] = None
    lock = threading.Lock()


class _DistilBERTModelHolder:
    pipe = None
    error: Optional[str] = None
    lock = threading.Lock()


def _load_pipeline():
    """Instantiate the primary HuggingFace pipeline. Called once, under a lock."""
    global ACTIVE_MODEL_NAME, ACTIVE_MODEL_F1
    from transformers import pipeline

    logger.info(
        "ml.loading_model",
        model=_settings.HF_MODEL_NAME,
        device=_settings.ML_DEVICE,
    )
    pipe = pipeline(
        task="text-classification",
        model=_settings.HF_MODEL_NAME,
        tokenizer=_settings.HF_MODEL_NAME,
        device=0 if _settings.ML_DEVICE == "cuda" else -1,
        top_k=None,
        truncation=True,
    )
    ACTIVE_MODEL_NAME = _settings.HF_MODEL_NAME
    ACTIVE_MODEL_F1 = 0.92  # Published benchmark for hateBERT on RAL-E
    logger.info("ml.model_loaded", model=_settings.HF_MODEL_NAME)

    # Kick off fallback loading in a background thread.
    t = threading.Thread(target=_load_fallback_pipeline, daemon=True)
    t.start()

    return pipe


def _load_fallback_pipeline():
    """Instantiate the fallback HuggingFace pipeline. Runs in a background thread."""
    from transformers import pipeline as hf_pipeline

    with _FallbackModelHolder.lock:
        if _FallbackModelHolder.pipe is not None or _FallbackModelHolder.error is not None:
            return
        try:
            logger.info(
                "ml.loading_fallback_model",
                model=_settings.HF_FALLBACK_MODEL_NAME,
                device=_settings.ML_DEVICE,
            )
            _FallbackModelHolder.pipe = hf_pipeline(
                task="text-classification",
                model=_settings.HF_FALLBACK_MODEL_NAME,
                tokenizer=_settings.HF_FALLBACK_MODEL_NAME,
                device=0 if _settings.ML_DEVICE == "cuda" else -1,
                top_k=None,
                truncation=True,
            )
            logger.info("ml.fallback_model_loaded", model=_settings.HF_FALLBACK_MODEL_NAME)
        except Exception as exc:
            _FallbackModelHolder.error = str(exc)
            logger.error("ml.fallback_model_load_failed", error=str(exc))


def get_pipeline():
    """Return the primary classifier pipeline, loading on first use."""
    if _ModelHolder.pipe is not None or _ModelHolder.error is not None:
        return _ModelHolder.pipe

    with _ModelHolder.lock:
        if _ModelHolder.pipe is None and _ModelHolder.error is None:
            try:
                _ModelHolder.pipe = _load_pipeline()
            except Exception as exc:
                _ModelHolder.error = str(exc)
                logger.error("ml.model_load_failed", error=str(exc))
    return _ModelHolder.pipe


def get_fallback_pipeline():
    """Return the fallback classifier pipeline (may be None if not yet loaded)."""
    return _FallbackModelHolder.pipe


def _load_sgd_model():
    """Load the scikit-learn SGD pipeline from disk. Called under a lock."""
    import joblib

    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "models", "sgd_threat_model.joblib",
    )
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"SGD model not found at {model_path}")
    pipe = joblib.load(model_path)
    logger.info("ml.sgd_model_loaded", path=model_path)
    return pipe


def get_sgd_pipeline():
    """Return the SGD classifier pipeline, loading from disk on first use."""
    if _SGDModelHolder.pipe is not None or _SGDModelHolder.error is not None:
        return _SGDModelHolder.pipe

    with _SGDModelHolder.lock:
        if _SGDModelHolder.pipe is None and _SGDModelHolder.error is None:
            try:
                _SGDModelHolder.pipe = _load_sgd_model()
            except Exception as exc:
                _SGDModelHolder.error = str(exc)
                logger.error("ml.sgd_model_load_failed", error=str(exc))
    return _SGDModelHolder.pipe


def _load_sklearn_model(filename: str, label: str):
    """Generic loader for scikit-learn joblib models."""
    import joblib
    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "models", filename,
    )
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"{label} model not found at {model_path}")
    pipe = joblib.load(model_path)
    logger.info(f"ml.{label.lower()}_model_loaded", path=model_path)
    return pipe


def get_rf_pipeline():
    """Return the Random Forest classifier pipeline, loading from disk on first use."""
    if _RFModelHolder.pipe is not None or _RFModelHolder.error is not None:
        return _RFModelHolder.pipe
    with _RFModelHolder.lock:
        if _RFModelHolder.pipe is None and _RFModelHolder.error is None:
            try:
                _RFModelHolder.pipe = _load_sklearn_model("rf_threat_model.joblib", "RandomForest")
            except Exception as exc:
                _RFModelHolder.error = str(exc)
                logger.error("ml.rf_model_load_failed", error=str(exc))
    return _RFModelHolder.pipe


def get_linsvc_pipeline():
    """Return the Linear SVC classifier pipeline, loading from disk on first use."""
    if _LinSVCModelHolder.pipe is not None or _LinSVCModelHolder.error is not None:
        return _LinSVCModelHolder.pipe
    with _LinSVCModelHolder.lock:
        if _LinSVCModelHolder.pipe is None and _LinSVCModelHolder.error is None:
            try:
                _LinSVCModelHolder.pipe = _load_sklearn_model("linsvc_threat_model.joblib", "LinearSVC")
            except Exception as exc:
                _LinSVCModelHolder.error = str(exc)
                logger.error("ml.linsvc_model_load_failed", error=str(exc))
    return _LinSVCModelHolder.pipe


def _load_distilbert_pipeline():
    """Instantiate the DistilBERT HuggingFace pipeline. Called under a lock."""
    from transformers import pipeline as hf_pipeline

    logger.info("ml.loading_distilbert_model", model=_settings.HF_DISTILBERT_MODEL_NAME)
    pipe = hf_pipeline(
        task="text-classification",
        model=_settings.HF_DISTILBERT_MODEL_NAME,
        tokenizer=_settings.HF_DISTILBERT_MODEL_NAME,
        device=0 if _settings.ML_DEVICE == "cuda" else -1,
        top_k=None,
        truncation=True,
    )
    logger.info("ml.distilbert_model_loaded", model=_settings.HF_DISTILBERT_MODEL_NAME)
    return pipe


def get_distilbert_pipeline():
    """Return the DistilBERT pipeline, loading on first use."""
    if _DistilBERTModelHolder.pipe is not None or _DistilBERTModelHolder.error is not None:
        return _DistilBERTModelHolder.pipe
    with _DistilBERTModelHolder.lock:
        if _DistilBERTModelHolder.pipe is None and _DistilBERTModelHolder.error is None:
            try:
                _DistilBERTModelHolder.pipe = _load_distilbert_pipeline()
            except Exception as exc:
                _DistilBERTModelHolder.error = str(exc)
                logger.error("ml.distilbert_model_load_failed", error=str(exc))
    return _DistilBERTModelHolder.pipe


def reload_sklearn_models() -> Dict[str, bool]:
    """Force reload all sklearn models from disk (called after retraining)."""
    results = {}
    for holder, filename, label in [
        (_SGDModelHolder, "sgd_threat_model.joblib", "sgd"),
        (_RFModelHolder, "rf_threat_model.joblib", "rf"),
        (_LinSVCModelHolder, "linsvc_threat_model.joblib", "linsvc"),
    ]:
        with holder.lock:
            holder.pipe = None
            holder.error = None
        try:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "data", "models", filename,
            )
            if os.path.exists(model_path):
                import joblib
                holder.pipe = joblib.load(model_path)
                results[label] = True
                logger.info(f"ml.{label}_model_reloaded", path=model_path)
            else:
                holder.error = f"File not found: {model_path}"
                results[label] = False
        except Exception as exc:
            holder.error = str(exc)
            results[label] = False
    return results


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def _score_to_level(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"


_THREAT_LABEL_TOKENS = (
    "toxic", "severe", "threat", "hate", "insult", "identity",
    "obscene", "harass", "offensive", "abuse", "extreme",
)


def _is_threat_label(label: str) -> bool:
    lower = label.lower()
    if lower in {"label_1", "positive", "toxic"}:
        return True
    return any(tok in lower for tok in _THREAT_LABEL_TOKENS)


def _chunk(text: str, size: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    return [text[i : i + size] for i in range(0, len(text), size)]


def _run_pipeline(pipe: object, text: str) -> Dict[str, float]:
    """Run a single HF pipeline on text chunks and return averaged label scores."""
    chunks = _chunk(text, _settings.ML_MAX_CHARS)
    if not chunks:
        return {}

    totals: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for chunk_text in chunks:
        raw = pipe(chunk_text)  # type: ignore[operator]
        if isinstance(raw, list) and raw and isinstance(raw[0], list):
            raw = raw[0]
        for item in raw:
            label = item["label"]
            score = float(item["score"])
            totals[label] = totals.get(label, 0.0) + score
            counts[label] = counts.get(label, 0) + 1

    return {lbl: round(totals[lbl] / counts[lbl], 4) for lbl in totals}


def _extract_threat_score(label_scores: Dict[str, float]) -> float:
    """Compute single threat score from label_scores dict.

    Only labels that match known threat/hate vocabulary contribute to the
    score.  When the loaded model uses non-threat labels (e.g. a sentiment
    model with POSITIVE/NEGATIVE), we return 0.0 rather than mis-treating
    the max confidence as a threat signal.
    """
    threat_candidates = [
        score for lbl, score in label_scores.items() if _is_threat_label(lbl)
    ]
    if threat_candidates:
        return max(threat_candidates)
    return 0.0


def get_available_models() -> List[Dict[str, str]]:
    """Return a list of available ML models."""
    models: List[Dict[str, str]] = []

    _model_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "models",
    )

    sklearn_models = [
        ("rf_threat_model.joblib", "rf", "Random Forest", "Random Forest with TF-IDF (ensemble of decision trees)"),
        ("sgd_threat_model.joblib", "sgd", "SGD Classifier", "SGD Classifier with TF-IDF (fast, lightweight)"),
        ("linsvc_threat_model.joblib", "linsvc", "Linear SVC", "Calibrated Linear SVC with TF-IDF (high accuracy)"),
    ]
    for filename, model_id, model_name, desc in sklearn_models:
        trained = os.path.exists(os.path.join(_model_dir, filename))
        models.append({
            "id": model_id,
            "name": model_name,
            "type": "traditional_ml",
            "description": desc if trained else f"{desc} — not yet trained, run training first",
            "available": "true" if trained else "false",
        })

    if _settings.HF_MODEL_NAME:
        models.append({
            "id": "hatebert",
            "name": "HateBERT",
            "type": "hf_bert",
            "description": "GroNLP/hateBERT — pre-trained on Reddit hate speech for extremism detection",
        })

    if _settings.HF_DISTILBERT_MODEL_NAME:
        models.append({
            "id": "distilbert",
            "name": "Distilled BERT Model",
            "type": "hf_distilbert",
            "description": "DistilBERT — lightweight BERT for fast sentiment/threat classification",
        })

    # Always add an "all" option to run every loaded model equally
    models.append({
        "id": "all",
        "name": "All Models (Equal Weighting)",
        "type": "all",
        "description": "Run all available models and average scores equally",
    })

    return models


def _classify_sync(text: str, model: str = "distilbert") -> Dict[str, Any]:
    """Run the classifier(s) on text.
    
    Args:
        text: The text to classify
        model: Which model to use: 'rf', 'sgd', 'linsvc', 'hatebert', 'distilbert', or 'all'
    """
    # Handle 'all' — delegate to multi-model classification
    if model == "all":
        return _classify_all_models_sync(text)

    # Handle sklearn models
    if model in ("sgd", "rf", "linsvc"):
        return _classify_sklearn_sync(text, model)

    # Handle HateBERT
    if model == "hatebert":
        return _classify_hf_sync(text, "hatebert")

    # Handle DistilBERT (default)
    return _classify_hf_sync(text, "distilbert")


def _classify_sklearn_sync(text: str, model: str) -> Dict[str, Any]:
    """Run a scikit-learn model on text and return normalized result."""
    getter_map = {
        "sgd": (get_sgd_pipeline, _SGDModelHolder, "SGD Classifier"),
        "rf": (get_rf_pipeline, _RFModelHolder, "Random Forest"),
        "linsvc": (get_linsvc_pipeline, _LinSVCModelHolder, "Linear SVC"),
    }
    getter, holder, label = getter_map[model]
    pipe = getter()
    if pipe is None:
        return {
            "method": "unavailable",
            "model": label,
            "error": holder.error or f"{label} model not loaded",
            "threat_score": 0.0,
            "threat_level": "low",
            "label_scores": {},
            "top_label": None,
            "ensemble": False,
            "models_used": [],
        }
    try:
        text_input = (text or "").strip()
        proba = pipe.predict_proba([text_input])[0]
        classes = list(pipe.classes_)
        label_scores = {cls: round(float(p), 4) for cls, p in zip(classes, proba)}
        high_score = label_scores.get("high", 0.0)
        return {
            "method": f"{model}_pipeline",
            "model": label,
            "threat_score": high_score,
            "threat_level": _score_to_level(high_score),
            "label_scores": label_scores,
            "top_label": max(label_scores, key=label_scores.get),
            "ensemble": False,
            "models_used": [label],
        }
    except Exception as exc:
        logger.error(f"ml.{model}_inference_failed", error=str(exc))
        return {
            "method": "unavailable",
            "model": label,
            "error": str(exc),
            "threat_score": 0.0,
            "threat_level": "low",
            "label_scores": {},
            "top_label": None,
            "ensemble": False,
            "models_used": [],
        }


def _classify_hf_sync(text: str, model: str) -> Dict[str, Any]:
    """Run a HuggingFace model by key (hatebert, distilbert)."""
    getter_map = {
        "hatebert": (get_pipeline, _ModelHolder, _settings.HF_MODEL_NAME),
        "distilbert": (get_distilbert_pipeline, _DistilBERTModelHolder, _settings.HF_DISTILBERT_MODEL_NAME),
    }
    getter, holder, model_name = getter_map[model]
    pipe = getter()
    if pipe is None:
        return {
            "method": "unavailable",
            "model": model_name,
            "error": holder.error or f"{model} not loaded",
            "threat_score": 0.0,
            "threat_level": "low",
            "label_scores": {},
            "top_label": None,
            "ensemble": False,
            "models_used": [],
        }
    try:
        label_scores = _run_pipeline(pipe, text)
        threat_score = _extract_threat_score(label_scores)
        top_label = max(label_scores, key=label_scores.get) if label_scores else None
        return {
            "method": "hf_pipeline",
            "model": model_name,
            "threat_score": round(float(threat_score), 4),
            "threat_level": _score_to_level(float(threat_score)),
            "label_scores": label_scores,
            "top_label": top_label,
            "ensemble": False,
            "models_used": [model_name],
        }
    except Exception as exc:
        logger.error(f"ml.{model}_inference_failed", error=str(exc))
        return {
            "method": "unavailable",
            "model": model_name,
            "error": str(exc),
            "threat_score": 0.0,
            "threat_level": "low",
            "label_scores": {},
            "top_label": None,
            "ensemble": False,
            "models_used": [],
        }


def _classify_all_models_sync(text: str) -> Dict[str, Any]:
    """Run all available models and return equally weighted average threat score.
    
    Returns the standard result shape plus 'per_model_scores' dict.
    """
    scores: Dict[str, float] = {}
    per_model: Dict[str, Dict] = {}

    _model_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "models",
    )

    # sklearn models
    for model_id, filename, label in [
        ("rf", "rf_threat_model.joblib", "Random Forest"),
        ("sgd", "sgd_threat_model.joblib", "SGD Classifier"),
        ("linsvc", "linsvc_threat_model.joblib", "Linear SVC"),
    ]:
        if os.path.exists(os.path.join(_model_dir, filename)):
            r = _classify_sklearn_sync(text, model_id)
            if r["method"] != "unavailable":
                scores[label] = r["threat_score"]
                per_model[label] = r

    # HateBERT
    try:
        hatebert_result = _classify_hf_sync(text, "hatebert")
        if hatebert_result.get("method") != "unavailable":
            scores["HateBERT"] = hatebert_result["threat_score"]
            per_model["HateBERT"] = hatebert_result
    except Exception as exc:
        logger.warning("ml.all_hatebert_failed", error=str(exc))

    # DistilBERT
    try:
        distilbert_result = _classify_hf_sync(text, "distilbert")
        if distilbert_result.get("method") != "unavailable":
            scores["Distilled BERT Model"] = distilbert_result["threat_score"]
            per_model["Distilled BERT Model"] = distilbert_result
    except Exception as exc:
        logger.warning("ml.all_distilbert_failed", error=str(exc))

    if not scores:
        return {
            "method": "unavailable",
            "model": "All Models",
            "error": "No models available",
            "threat_score": 0.0,
            "threat_level": "low",
            "label_scores": {},
            "top_label": None,
            "ensemble": True,
            "models_used": [],
            "per_model_scores": {},
        }

    avg_score = sum(scores.values()) / len(scores)
    return {
        "method": "all_models",
        "model": "All Models (Equal Weights)",
        "threat_score": round(float(avg_score), 4),
        "threat_level": _score_to_level(float(avg_score)),
        "label_scores": {},
        "top_label": None,
        "ensemble": True,
        "models_used": list(scores.keys()),
        "per_model_scores": scores,
        "per_model_details": per_model,
    }


def classify_with_models_sync(text: str, model_ids: List[str]) -> Dict[str, Any]:
    """Classify text with a specific list of model IDs, average scores equally.
    
    Args:
        text: Text to classify
        model_ids: List of model IDs (e.g. ['sgd', 'rf', 'distilbert']).
                   Pass ['all'] to run all available models.
    
    Returns dict with overall threat_score (equal-weight avg), per_model_scores, etc.
    """
    if not model_ids or model_ids == ["all"]:
        return _classify_all_models_sync(text)
    if len(model_ids) == 1:
        return _classify_sync(text, model_ids[0])

    scores: Dict[str, float] = {}
    per_model: Dict[str, Dict] = {}
    for mid in model_ids:
        r = _classify_sync(text, mid)
        if r.get("method") != "unavailable":
            scores[r.get("model", mid)] = r["threat_score"]
            per_model[r.get("model", mid)] = r

    if not scores:
        return {
            "method": "unavailable",
            "model": "Selected Models",
            "error": "None of the selected models could run",
            "threat_score": 0.0,
            "threat_level": "low",
            "label_scores": {},
            "top_label": None,
            "ensemble": True,
            "models_used": [],
            "per_model_scores": {},
        }

    avg_score = sum(scores.values()) / len(scores)
    return {
        "method": "multi_model",
        "model": f"Selected Models ({', '.join(model_ids)})",
        "threat_score": round(float(avg_score), 4),
        "threat_level": _score_to_level(float(avg_score)),
        "label_scores": {},
        "top_label": None,
        "ensemble": True,
        "models_used": list(scores.keys()),
        "per_model_scores": scores,
        "per_model_details": per_model,
    }


# ---------------------------------------------------------------------------
# SHAP explainability (optional)
# ---------------------------------------------------------------------------


def explain_prediction(text: str) -> dict:
    """
    Use SHAP to compute token-level attribution scores for the primary model prediction.
    Returns a dict with keys:
      - "tokens": list[str]         — tokenized input words
      - "shap_values": list[float]  — SHAP value per token (positive = pushes toward threat)
      - "base_value": float         — baseline threat score
      - "prediction": float         — final model output threat score
    Falls back to {"error": "<reason>"} if shap is not installed or model unavailable.
    """
    try:
        import shap  # noqa: F811
    except ImportError:
        return {"error": "shap package is not installed"}

    pipe = get_pipeline()
    if pipe is None:
        return {"error": _ModelHolder.error or "pipeline not loaded"}

    try:
        truncated = (text or "")[:512]
        explainer = shap.Explainer(pipe)
        shap_values = explainer([truncated])

        # shap_values is a shap.Explanation object
        tokens = shap_values.data[0].tolist() if hasattr(shap_values.data[0], "tolist") else list(shap_values.data[0])
        values = shap_values.values[0]

        # For multi-label models, pick the threat-bearing class column.
        if values.ndim > 1:
            # Find best threat-label column index
            output_names = shap_values.output_names if hasattr(shap_values, "output_names") else []
            threat_col = 0
            for idx, name in enumerate(output_names):
                if _is_threat_label(str(name)):
                    threat_col = idx
                    break
            values = values[:, threat_col]

        shap_list = values.tolist() if hasattr(values, "tolist") else list(values)
        base_value = float(shap_values.base_values[0]) if hasattr(shap_values.base_values[0], "__float__") else 0.0

        return {
            "tokens": tokens,
            "shap_values": [round(v, 6) for v in shap_list],
            "base_value": round(base_value, 6),
            "prediction": round(float(sum(shap_list) + base_value), 6),
        }
    except Exception as exc:
        logger.warning("ml.shap_explain_failed", error=str(exc))
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Async service class
# ---------------------------------------------------------------------------


class MLService:
    """Thin async wrapper so FastAPI handlers can `await` classification."""

    async def classify(self, text: str, explain: bool = False, model: str = "ensemble") -> Dict[str, Any]:
        result = await asyncio.to_thread(_classify_sync, text, model)
        if explain:
            explanation = await asyncio.to_thread(explain_prediction, text)
            result["explanation"] = explanation
        return result

    async def classify_with_models(self, text: str, model_ids: List[str]) -> Dict[str, Any]:
        """Classify with multiple models, averaging scores equally."""
        return await asyncio.to_thread(classify_with_models_sync, text, model_ids)

    def classify_sync(self, text: str, model: str = "ensemble") -> Dict[str, Any]:
        return _classify_sync(text, model)
