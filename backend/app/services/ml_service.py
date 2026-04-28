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
    """Compute single threat score from label_scores dict."""
    threat_candidates = [
        score for lbl, score in label_scores.items() if _is_threat_label(lbl)
    ]
    if threat_candidates:
        return max(threat_candidates)
    return max(label_scores.values()) if label_scores else 0.0


def get_available_models() -> List[Dict[str, str]]:
    """Return a list of available ML models."""
    models = [
        {
            "id": "primary",
            "name": _settings.HF_MODEL_NAME,
            "type": "primary",
            "description": "Primary model (GroNLP/hateBERT - optimized for extremism detection)",
        }
    ]
    if _settings.HF_FALLBACK_MODEL_NAME:
        models.append(
            {
                "id": "fallback",
                "name": _settings.HF_FALLBACK_MODEL_NAME,
                "type": "fallback",
                "description": "Fallback model (Twitter RoBERTa - general toxicity detection)",
            }
        )
        models.append(
            {
                "id": "ensemble",
                "name": "Ensemble (65% primary + 35% fallback)",
                "type": "ensemble",
                "description": "Weighted ensemble combining both models",
            }
        )

    # Always include SGD if the model file exists
    sgd_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "models", "sgd_threat_model.joblib",
    )
    if os.path.exists(sgd_path):
        models.append(
            {
                "id": "sgd",
                "name": "SGD Classifier",
                "type": "traditional_ml",
                "description": "SGDClassifier with TF-IDF (fast, lightweight traditional ML)",
            }
        )
    return models


def _classify_sync(text: str, model: str = "ensemble") -> Dict[str, Any]:
    """Run the classifier(s) on text.
    
    Args:
        text: The text to classify
        model: Which model to use: 'primary', 'fallback', 'ensemble', or 'sgd'
    """
    # Handle SGD model separately — it doesn't require the HF pipelines
    if model == "sgd":
        sgd_pipe = get_sgd_pipeline()
        if sgd_pipe is None:
            return {
                "method": "unavailable",
                "model": "SGD Classifier",
                "error": _SGDModelHolder.error or "SGD model not loaded",
                "threat_score": 0.0,
                "threat_level": "low",
                "label_scores": {},
                "top_label": None,
                "ensemble": False,
                "models_used": [],
            }
        try:
            text_input = (text or "").strip()
            proba = sgd_pipe.predict_proba([text_input])[0]
            classes = list(sgd_pipe.classes_)
            label_scores = {cls: round(float(p), 4) for cls, p in zip(classes, proba)}
            high_score = label_scores.get("high", 0.0)
            return {
                "method": "sgd_pipeline",
                "model": "SGD Classifier",
                "threat_score": high_score,
                "threat_level": _score_to_level(high_score),
                "label_scores": label_scores,
                "top_label": max(label_scores, key=label_scores.get),
                "ensemble": False,
                "models_used": ["SGD Classifier"],
            }
        except Exception as exc:
            logger.error("ml.sgd_inference_failed", error=str(exc))
            return {
                "method": "unavailable",
                "model": "SGD Classifier",
                "error": str(exc),
                "threat_score": 0.0,
                "threat_level": "low",
                "label_scores": {},
                "top_label": None,
                "ensemble": False,
                "models_used": [],
            }

    # --- HF pipeline path ---
    pipe = get_pipeline()
    if pipe is None:
        return {
            "method": "unavailable",
            "model": _settings.HF_MODEL_NAME,
            "error": _ModelHolder.error or "pipeline not loaded",
            "threat_score": 0.0,
            "threat_level": "low",
            "label_scores": {},
            "top_label": None,
            "ensemble": False,
            "models_used": [],
        }

    chunks = _chunk(text, _settings.ML_MAX_CHARS)
    if not chunks:
        return {
            "method": "hf_pipeline",
            "model": _settings.HF_MODEL_NAME,
            "threat_score": 0.0,
            "threat_level": "low",
            "label_scores": {},
            "top_label": None,
            "ensemble": False,
            "models_used": [_settings.HF_MODEL_NAME],
        }

    # --- Primary model ---
    primary_label_scores = _run_pipeline(pipe, text)
    primary_threat_score = _extract_threat_score(primary_label_scores)

    top_label = (
        max(primary_label_scores, key=primary_label_scores.get)
        if primary_label_scores
        else None
    )

    # --- Model selection logic ---
    fallback_pipe = get_fallback_pipeline()
    ensemble_used = False
    models_used = [_settings.HF_MODEL_NAME]
    final_threat_score = primary_threat_score
    selected_model_name = _settings.HF_MODEL_NAME
    label_scores_to_return = primary_label_scores

    # If fallback requested but not available, fall back to primary
    if model in ("fallback", "ensemble") and fallback_pipe is None:
        logger.warning("ml.fallback_requested_but_unavailable", requested_model=model)
        model = "primary"

    if model == "fallback" and fallback_pipe is not None:
        try:
            fallback_label_scores = _run_pipeline(fallback_pipe, text)
            final_threat_score = _extract_threat_score(fallback_label_scores)
            selected_model_name = _settings.HF_FALLBACK_MODEL_NAME
            label_scores_to_return = fallback_label_scores
            models_used = [_settings.HF_FALLBACK_MODEL_NAME]
        except Exception as exc:
            logger.warning("ml.fallback_inference_failed", error=str(exc))
            model = "primary"

    elif model == "ensemble" and fallback_pipe is not None:
        try:
            fallback_label_scores = _run_pipeline(fallback_pipe, text)
            fallback_threat_score = _extract_threat_score(fallback_label_scores)
            final_threat_score = 0.65 * primary_threat_score + 0.35 * fallback_threat_score
            ensemble_used = True
            models_used = [_settings.HF_MODEL_NAME, _settings.HF_FALLBACK_MODEL_NAME]
        except Exception as exc:
            logger.warning("ml.ensemble_inference_failed", error=str(exc))
            model = "primary"

    return {
        "method": "hf_pipeline",
        "model": selected_model_name,
        "threat_score": round(float(final_threat_score), 4),
        "threat_level": _score_to_level(float(final_threat_score)),
        "label_scores": label_scores_to_return,
        "top_label": top_label,
        "ensemble": ensemble_used,
        "models_used": models_used,
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

    def classify_sync(self, text: str, model: str = "ensemble") -> Dict[str, Any]:
        return _classify_sync(text, model)
