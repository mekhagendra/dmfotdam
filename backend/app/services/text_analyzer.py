"""
Text analysis service.

Responsibilities:
  * Extract raw text from files (PDF, DOCX, TXT, CSV, XLSX, JSON).
  * Feed the text to the pretrained HuggingFace classifier via `MLService`.
  * Return a normalized analysis dict consumed by the API + DB.

This module intentionally has NO rule-based keyword matching — the classifier
is authoritative. Keyword extraction shown in the `keywords` field is just
the most frequent non-trivial tokens, used for UI display, not scoring.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict

from app.core.logging import get_logger
from app.services.ml_service import MLService

logger = get_logger(__name__)


class TextAnalyzer:
    """Extract text from files and classify it with the ML service."""

    def __init__(self) -> None:
        self._ml = MLService()

    # ------------------------------------------------------------------ extraction

    def extract_text_from_file(self, file_path: str, file_type: str) -> str:
        """Dispatch by extension."""
        file_type = (file_type or "").lower().lstrip(".")
        if file_type == "txt":
            return self._read_text(file_path)
        if file_type == "pdf":
            return self._extract_pdf(file_path)
        if file_type == "docx":
            return self._extract_docx(file_path)
        if file_type == "csv":
            return self._extract_csv(file_path)
        if file_type in ("xlsx", "xls"):
            return self._extract_excel(file_path)
        if file_type == "json":
            return self._extract_json(file_path)
        raise ValueError(f"Unsupported file type: {file_type}")

    def _read_text(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _extract_pdf(self, file_path: str) -> str:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            logger.warning("PyPDF2 not installed")
            return ""
        reader = PdfReader(file_path)
        return "\n".join((p.extract_text() or "") for p in reader.pages)

    def _extract_docx(self, file_path: str) -> str:
        try:
            from docx import Document
        except ImportError:
            logger.warning("python-docx not installed")
            return ""
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text)

    def _extract_csv(self, file_path: str) -> str:
        import pandas as pd
        df = pd.read_csv(
            file_path, encoding="utf-8", on_bad_lines="skip", low_memory=False
        )
        text_cols = df.select_dtypes(include=["object"]).columns.tolist()
        if not text_cols:
            return df.to_string(max_rows=500)
        return "\n".join(
            " ".join(str(v) for v in row if pd.notna(v))
            for _, row in df[text_cols].head(5000).iterrows()
        )

    def _extract_excel(self, file_path: str) -> str:
        import pandas as pd
        df = pd.read_excel(file_path, engine="openpyxl")
        text_cols = df.select_dtypes(include=["object"]).columns.tolist()
        if not text_cols:
            return df.to_string(max_rows=500)
        return "\n".join(
            " ".join(str(v) for v in row if pd.notna(v))
            for _, row in df[text_cols].head(5000).iterrows()
        )

    def _extract_json(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        def flatten(obj, depth=0):
            if depth > 10:
                return []
            parts = []
            if isinstance(obj, dict):
                for v in obj.values():
                    parts.extend(flatten(v, depth + 1))
            elif isinstance(obj, list):
                for item in obj[:5000]:
                    parts.extend(flatten(item, depth + 1))
            elif isinstance(obj, str):
                parts.append(obj)
            return parts

        return "\n".join(flatten(data))

    # ------------------------------------------------------------------ analysis

    async def analyze(self, text: str, explain: bool = False) -> Dict[str, Any]:
        """Run the classifier and return a normalized analysis result."""
        if not text or not text.strip():
            return self._empty_result()

        ml = await self._ml.classify(text, explain=explain)

        threat_score = float(ml.get("threat_score", 0.0))
        threat_level = ml.get("threat_level", "low")
        method = ml.get("method", "unavailable")

        keywords = self._top_keywords(text)
        language = self._detect_language(text)
        summary = self._build_summary(threat_level, threat_score, ml)

        return {
            "threat_score": threat_score,
            "threat_level": threat_level,
            "summary": summary,
            "details": {
                "ml": {k: v for k, v in ml.items() if k not in ("method", "explanation")},
                "analysis_method": method,
                "word_count": len(text.split()),
            },
            "keywords": keywords,
            "sentiment": None,   # deliberately not produced by rule engine
            "language": language,
            "explanation": ml.get("explanation"),
        }

    async def analyze_file(self, file_path: str, file_type: str) -> Dict[str, Any]:
        text = self.extract_text_from_file(file_path, file_type)
        return await self.analyze(text)

    # ------------------------------------------------------------------ helpers

    def _top_keywords(self, text: str, limit: int = 15) -> list[str]:
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        if not words:
            return []
        freq = Counter(words)
        return [w for w, _ in freq.most_common(limit)]

    def _detect_language(self, text: str) -> str:
        try:
            from langdetect import detect
            return detect(text)
        except Exception:
            return "unknown"

    def _build_summary(
        self, level: str, score: float, ml: Dict[str, Any]
    ) -> str:
        if ml.get("method") == "unavailable":
            return (
                f"ML classifier unavailable ({ml.get('error', 'unknown error')}). "
                "No reliable threat score could be produced."
            )

        top_label = ml.get("top_label") or "n/a"
        parts = [
            f"Threat level: {level.upper()} (score: {score:.2f}).",
            f"Top label: {top_label}.",
        ]
        if level in {"high", "critical"}:
            parts.append("Recommended: human review before action.")
        return " ".join(parts)

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "threat_score": 0.0,
            "threat_level": "low",
            "summary": "No content to analyze.",
            "details": {},
            "keywords": [],
            "sentiment": None,
            "language": "unknown",
        }
