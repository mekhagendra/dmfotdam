"""
Machine learning service for extremism/threat classification.

Supports two backends:
  1. scikit-learn TF-IDF model  (threat_level_model.joblib)
  2. BERT / DistilBERT model    (bert_threat_model/)

The service prefers BERT when available and falls back to sklearn.
"""

import json
import os

import joblib
import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

# Resolve model directory relative to this file
_MODEL_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "data", "models"
)

# Threat-level label → numeric score mapping
_LEVEL_SCORES = {
    "low": 0.10,
    "medium": 0.40,
    "high": 0.65,
    "critical": 0.90,
}


class MLService:
    """Singleton-style service that loads trained models once and exposes classify()."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._threat_model = None
            cls._instance._bert_model = None
            cls._instance._bert_tokenizer = None
            cls._instance._bert_label_config = None
            cls._instance._loaded = False
        return cls._instance

    # ── loading ───────────────────────────────────────────────────────
    def load_models(self) -> bool:
        """Load available models from disk. Returns True if at least one is available."""
        if self._loaded:
            return self._threat_model is not None or self._bert_model is not None

        # Try loading BERT model first
        self._load_bert_model()

        # Also load sklearn model as fallback
        threat_path = os.path.join(_MODEL_DIR, "threat_level_model.joblib")
        try:
            self._threat_model = joblib.load(threat_path)
            logger.info("Threat-level sklearn model loaded", path=threat_path)
        except Exception as e:
            logger.warning("Could not load sklearn threat-level model", error=str(e))
            self._threat_model = None

        self._loaded = True
        return self._threat_model is not None or self._bert_model is not None

    def _load_bert_model(self):
        """Load BERT/DistilBERT model and tokenizer if available."""
        bert_dir = os.path.join(_MODEL_DIR, "bert_threat_model")
        label_config_path = os.path.join(bert_dir, "label_config.json")

        if not os.path.isdir(bert_dir):
            logger.info("No BERT model directory found, skipping")
            return

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._bert_tokenizer = AutoTokenizer.from_pretrained(bert_dir)
            self._bert_model = AutoModelForSequenceClassification.from_pretrained(bert_dir)
            self._bert_model.eval()

            # Use GPU/MPS if available
            if torch.cuda.is_available():
                self._bert_model = self._bert_model.to("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._bert_model = self._bert_model.to("mps")

            # Load label mapping
            if os.path.exists(label_config_path):
                with open(label_config_path) as f:
                    self._bert_label_config = json.load(f)
            else:
                self._bert_label_config = {
                    "id2label": {"0": "low", "1": "high"},
                }

            logger.info("BERT threat model loaded", path=bert_dir)
        except ImportError:
            logger.warning("transformers/torch not installed, BERT model unavailable")
        except Exception as e:
            logger.warning("Could not load BERT model", error=str(e))
            self._bert_model = None
            self._bert_tokenizer = None

    @property
    def is_available(self) -> bool:
        return self._threat_model is not None or self._bert_model is not None

    @property
    def active_method(self) -> str:
        if self._bert_model is not None:
            return "bert"
        if self._threat_model is not None:
            return "sklearn"
        return "unavailable"

    # ── inference ─────────────────────────────────────────────────────
    def classify(self, text: str) -> dict:
        """Run ML classification on arbitrary text.

        Prefers BERT when available, falls back to sklearn TF-IDF model.

        Returns dict with:
          ml_threat_level, ml_threat_score, ml_threat_probabilities, method
        """
        if not self._loaded:
            self.load_models()

        if self._bert_model is not None:
            return self._classify_bert(text)

        if self._threat_model is not None:
            return self._classify_sklearn(text)

        return {"method": "unavailable"}

    def _classify_bert(self, text: str) -> dict:
        """Classify text using the BERT model."""
        import torch

        result: dict = {"method": "bert"}
        try:
            device = next(self._bert_model.parameters()).device
            inputs = self._bert_tokenizer(
                text, truncation=True, padding="max_length",
                max_length=128, return_tensors="pt",
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._bert_model(**inputs)
                proba = torch.softmax(outputs.logits, dim=-1)[0].cpu().numpy()

            id2label = self._bert_label_config.get("id2label", {"0": "low", "1": "high"})
            pred_idx = int(np.argmax(proba))
            pred_label = id2label[str(pred_idx)]

            result["ml_threat_level"] = pred_label
            result["ml_threat_score"] = round(float(
                sum(proba[i] * _LEVEL_SCORES.get(id2label[str(i)], 0.1)
                    for i in range(len(proba)))
            ), 4)
            result["ml_threat_probabilities"] = {
                id2label[str(i)]: round(float(proba[i]), 4)
                for i in range(len(proba))
            }
        except Exception as e:
            logger.error("BERT prediction failed", error=str(e))
            # Fall back to sklearn if BERT fails
            if self._threat_model is not None:
                return self._classify_sklearn(text)

        return result

    def _classify_sklearn(self, text: str) -> dict:
        """Classify text using the sklearn TF-IDF model."""
        result: dict = {"method": "ml_model"}
        try:
            proba = self._threat_model.predict_proba([text])[0]
            classes = self._threat_model.classes_
            pred_idx = int(np.argmax(proba))
            pred_label = classes[pred_idx]

            result["ml_threat_level"] = pred_label
            result["ml_threat_score"] = round(float(
                sum(proba[i] * _LEVEL_SCORES.get(c, 0.1) for i, c in enumerate(classes))
            ), 4)
            result["ml_threat_probabilities"] = {
                c: round(float(proba[i]), 4) for i, c in enumerate(classes)
            }
        except Exception as e:
            logger.error("Threat-level prediction failed", error=str(e))

        return result
