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
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.services.ml_service import MLService, classify_with_models_sync

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

    async def analyze(self, text: str, explain: bool = False, model: str = "distilbert",
                      models: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run the classifier and return a normalized analysis result.
        
        Args:
            text: Text to analyze
            explain: Include SHAP explanations
            model: Single ML model to use
            models: List of model IDs to use (overrides model if provided)
        """
        if not text or not text.strip():
            return self._empty_result()

        if models and len(models) > 0:
            ml = await self._ml.classify_with_models(text, models)
        else:
            ml = await self._ml.classify(text, explain=explain, model=model)

        threat_score = float(ml.get("threat_score", 0.0))
        threat_level = ml.get("threat_level", "low")
        method = ml.get("method", "unavailable")
        # Always expose model scores in report payloads.
        # For single-model runs, normalize to a one-entry map.
        model_scores = ml.get("per_model_scores")
        if not model_scores:
            model_name = str(ml.get("model") or model or "distilbert")
            model_scores = {model_name: round(threat_score, 4)}

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
            "sentiment": None,
            "language": language,
            "explanation": ml.get("explanation"),
            "model_scores": model_scores,
        }

    async def analyze_file(self, file_path: str, file_type: str,
                           models: Optional[List[str]] = None) -> Dict[str, Any]:
        text = self.extract_text_from_file(file_path, file_type)
        return await self.analyze(text, models=models)

    async def analyze_document_rows(
        self, file_path: str, file_type: str, models: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze a CSV/Excel document row-by-row.
        
        Expects first row = header (discarded), first column = message text.
        Returns overall aggregate result plus per-row scores.
        """
        import pandas as pd
        import asyncio

        if file_type in ("csv",):
            df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip",
                             low_memory=False, header=0)
        else:
            df = pd.read_excel(file_path, engine="openpyxl", header=0)

        if df.empty:
            return self._empty_result()

        # First column = messages; header row already discarded by pandas
        msg_col = df.columns[0]
        messages = df[msg_col].dropna().astype(str).tolist()
        messages = [m.strip() for m in messages if m.strip()]

        if not messages:
            return self._empty_result()

        # Analyse each row
        row_results: List[Dict[str, Any]] = []
        threat_scores: List[float] = []
        aggregated_model_scores: Dict[str, List[float]] = {}

        model_ids = models if (models and len(models) > 0) else None

        for idx, msg in enumerate(messages[:5000]):  # cap at 5000 rows
            if model_ids:
                ml = await asyncio.to_thread(classify_with_models_sync, msg, model_ids)
            else:
                ml = await self._ml.classify(msg, model="distilbert")
            score = float(ml.get("threat_score", 0.0))
            threat_scores.append(score)
            row_model_scores = ml.get("per_model_scores")
            if not row_model_scores:
                model_name = str(ml.get("model") or "distilbert")
                row_model_scores = {model_name: round(score, 4)}

            for m_name, m_score in row_model_scores.items():
                aggregated_model_scores.setdefault(m_name, []).append(float(m_score))

            row_results.append({
                "row": idx + 2,  # +2 because row 1 is header
                "message": msg[:300],
                "threat_score": round(score, 4),
                "threat_level": ml.get("threat_level", "low"),
                "model_scores": row_model_scores,
            })

        avg_score = sum(threat_scores) / len(threat_scores) if threat_scores else 0.0
        from app.services.ml_service import _score_to_level
        threat_level = _score_to_level(avg_score)

        all_text = " ".join(messages[:500])
        keywords = self._top_keywords(all_text)
        language = self._detect_language(all_text[:2000])

        average_model_scores = {
            m_name: round(sum(scores) / len(scores), 4)
            for m_name, scores in aggregated_model_scores.items()
            if scores
        }

        return {
            "threat_score": round(avg_score, 4),
            "threat_level": threat_level,
            "summary": (
                f"Document analysis: {len(messages)} rows analysed. "
                f"Average threat score: {avg_score:.4f} ({threat_level.upper()})."
            ),
            "details": {
                "analysis_method": "row_by_row",
                "row_count": len(messages),
                "word_count": sum(len(m.split()) for m in messages),
            },
            "keywords": keywords,
            "sentiment": None,
            "language": language,
            "row_results": row_results,
            "model_scores": average_model_scores,
        }

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
