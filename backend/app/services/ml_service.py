"""
Machine learning service for extremism/threat classification.

Uses a scikit-learn model trained on the extremism dataset:
  threat_level_model  — classifies text → low / high
"""

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
            cls._instance._loaded = False
        return cls._instance

    # ── loading ───────────────────────────────────────────────────────
    def load_models(self) -> bool:
        """Load the threat model from disk. Returns True if available."""
        if self._loaded:
            return self._threat_model is not None

        threat_path = os.path.join(_MODEL_DIR, "threat_level_model.joblib")

        try:
            self._threat_model = joblib.load(threat_path)
            logger.info("Threat-level ML model loaded", path=threat_path)
        except Exception as e:
            logger.warning("Could not load threat-level model", error=str(e))
            self._threat_model = None

        self._loaded = True
        return self._threat_model is not None

    @property
    def is_available(self) -> bool:
        return self._threat_model is not None

    # ── inference ─────────────────────────────────────────────────────
    def classify(self, text: str) -> dict:
        """Run ML classification on arbitrary text.

        Returns dict with:
          ml_threat_level, ml_threat_score, ml_threat_probabilities, method
        """
        if not self._loaded:
            self.load_models()

        if self._threat_model is None:
            return {"method": "unavailable"}

        result: dict = {"method": "ml_model"}

        # ── threat level ──────────────────────────────────────────────
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
