"""
Text analysis service - NLP-based threat detection
"""

import csv
import io
import json
import os
import re
from collections import Counter

from app.core.logging import get_logger

logger = get_logger(__name__)

# Threat-related keyword categories for analysis
THREAT_KEYWORDS = {
    "violence": [
        "attack", "bomb", "explosive", "weapon", "assault", "destroy",
        "kill", "threat", "harm", "strike", "detonate", "ammunition",
    ],
    "extremism": [
        "radical", "extremist", "militant", "jihad", "insurgent",
        "propaganda", "radicalization", "fundamentalist", "recruit",
    ],
    "planning": [
        "plan", "target", "coordinate", "cell", "operation", "mission",
        "execute", "surveillance", "reconnaissance", "infiltrate",
    ],
    "financing": [
        "funding", "finance", "money laundering", "donation", "transfer",
        "cryptocurrency", "hawala", "smuggling",
    ],
}


class TextAnalyzer:
    """Service for analyzing text content for potential threats"""

    def extract_text_from_file(self, file_path: str, file_type: str) -> str:
        """Extract text from uploaded files"""
        if file_type == "txt":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        elif file_type == "pdf":
            return self._extract_pdf(file_path)
        elif file_type == "docx":
            return self._extract_docx(file_path)
        elif file_type == "csv":
            return self._extract_csv(file_path)
        elif file_type in ("xlsx", "xls"):
            return self._extract_excel(file_path)
        elif file_type == "json":
            return self._extract_json(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)
        except ImportError:
            logger.warning("PyPDF2 not available, returning empty text for PDF")
            return ""

    def _extract_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs if para.text)
        except ImportError:
            logger.warning("python-docx not available, returning empty text for DOCX")
            return ""

    def _extract_csv(self, file_path: str) -> str:
        """Extract text content from CSV by concatenating all cell values"""
        import pandas as pd
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip", low_memory=False)
        text_columns = df.select_dtypes(include=["object"]).columns.tolist()
        if not text_columns:
            return df.to_string(max_rows=500)
        return "\n".join(
            " ".join(str(v) for v in row if pd.notna(v))
            for _, row in df[text_columns].head(5000).iterrows()
        )

    def _extract_excel(self, file_path: str) -> str:
        """Extract text content from Excel files"""
        import pandas as pd
        df = pd.read_excel(file_path, engine="openpyxl")
        text_columns = df.select_dtypes(include=["object"]).columns.tolist()
        if not text_columns:
            return df.to_string(max_rows=500)
        return "\n".join(
            " ".join(str(v) for v in row if pd.notna(v))
            for _, row in df[text_columns].head(5000).iterrows()
        )

    def _extract_json(self, file_path: str) -> str:
        """Extract text content from JSON files"""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        def _flatten_values(obj, depth=0):
            if depth > 10:
                return []
            parts = []
            if isinstance(obj, dict):
                for v in obj.values():
                    parts.extend(_flatten_values(v, depth + 1))
            elif isinstance(obj, list):
                for item in obj[:5000]:
                    parts.extend(_flatten_values(item, depth + 1))
            elif isinstance(obj, str):
                parts.append(obj)
            return parts

        return "\n".join(_flatten_values(data))

    def analyze_data(self, file_path: str, file_type: str) -> dict:
        """Analyze structured data files (CSV/Excel/JSON) and return profiling + threat analysis"""
        import pandas as pd

        if file_type == "csv":
            df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip", low_memory=False)
        elif file_type in ("xlsx", "xls"):
            df = pd.read_excel(file_path, engine="openpyxl")
        elif file_type == "json":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.json_normalize(data) if not any(isinstance(v, list) for v in data.values()) else pd.DataFrame(next((v for v in data.values() if isinstance(v, list)), []))
            else:
                df = pd.DataFrame()
        else:
            raise ValueError(f"Unsupported data file type: {file_type}")

        # Data profiling
        profile = {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing_values": {col: int(v) for col, v in df.isnull().sum().items() if v > 0},
            "missing_pct": {col: round(v / len(df) * 100, 2) for col, v in df.isnull().sum().items() if v > 0},
        }

        # Numeric stats
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            stats = df[numeric_cols].describe().to_dict()
            profile["numeric_stats"] = {
                col: {k: round(v, 4) if isinstance(v, float) else v for k, v in col_stats.items()}
                for col, col_stats in stats.items()
            }

        # Categorical stats (top values)
        cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
        if cat_cols:
            profile["categorical_stats"] = {}
            for col in cat_cols[:20]:
                vc = df[col].value_counts().head(10)
                profile["categorical_stats"][col] = {
                    "unique": int(df[col].nunique()),
                    "top_values": {str(k): int(v) for k, v in vc.items()},
                }

        # Also run threat analysis on text content
        text = self.extract_text_from_file(file_path, file_type)
        threat_result = self.analyze(text)

        return {
            "analysis_type": "data_profiling",
            "data_profile": profile,
            "threat_analysis": threat_result,
        }

    def analyze(self, text: str) -> dict:
        """Perform full threat analysis on text"""
        if not text or not text.strip():
            return self._empty_result()

        text_lower = text.lower()
        words = re.findall(r'\b[a-z]+\b', text_lower)

        # Keyword matching (rule-based)
        keyword_hits = self._find_keywords(text_lower)

        # Rule-based threat score
        rule_score = self._calculate_threat_score(keyword_hits, len(words))
        rule_level = self._score_to_level(rule_score)

        # ML-based classification
        from app.services.ml_service import MLService
        ml = MLService()
        ml_result = ml.classify(text)

        if ml_result.get("method") == "ml_model":
            ml_score = ml_result.get("ml_threat_score", rule_score)
            ml_level = ml_result.get("ml_threat_level", rule_level)
            # Combined score: 70% ML + 30% rule-based
            threat_score = round(0.7 * ml_score + 0.3 * rule_score, 4)
            threat_level = self._score_to_level(threat_score)
        else:
            threat_score = rule_score
            threat_level = rule_level
            ml_result = {}

        # Extract top keywords
        word_freq = Counter(words)
        top_keywords = [w for w, _ in word_freq.most_common(20) if len(w) > 3]

        # Basic sentiment
        sentiment = self._basic_sentiment(text_lower)

        # Language detection
        language = self._detect_language(text)

        # Build summary
        summary = self._build_summary(threat_level, threat_score, keyword_hits, ml_result)

        return {
            "threat_score": threat_score,
            "threat_level": threat_level,
            "summary": summary,
            "details": {
                "keyword_hits": keyword_hits,
                "word_count": len(words),
                "categories_detected": list(keyword_hits.keys()),
                "ml_classification": {
                    k: v for k, v in ml_result.items() if k != "method"
                } if ml_result.get("method") == "ml_model" else None,
                "analysis_method": ml_result.get("method", "rule_based"),
            },
            "keywords": top_keywords[:15],
            "sentiment": sentiment,
            "language": language,
        }

    def _find_keywords(self, text: str) -> dict:
        """Find threat keywords in text, grouped by category"""
        hits = {}
        for category, keywords in THREAT_KEYWORDS.items():
            found = []
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                matches = re.findall(pattern, text)
                if matches:
                    found.append({"keyword": kw, "count": len(matches)})
            if found:
                hits[category] = found
        return hits

    def _calculate_threat_score(self, keyword_hits: dict, total_words: int) -> float:
        """Calculate 0–1 threat score based on keyword density and diversity"""
        if total_words == 0:
            return 0.0

        total_hit_count = sum(
            item["count"]
            for cat_hits in keyword_hits.values()
            for item in cat_hits
        )
        category_count = len(keyword_hits)

        # Density component (keyword hits / total words), capped at 0.5
        density = min(total_hit_count / max(total_words, 1), 0.5)

        # Diversity component (number of categories), capped at 0.5
        diversity = min(category_count / len(THREAT_KEYWORDS), 1.0) * 0.5

        return min(density + diversity, 1.0)

    def _score_to_level(self, score: float) -> str:
        if score >= 0.7:
            return "critical"
        elif score >= 0.5:
            return "high"
        elif score >= 0.3:
            return "medium"
        return "low"

    def _basic_sentiment(self, text: str) -> str:
        """Simple rule-based sentiment (placeholder for full NLP)"""
        positive_words = {"good", "peace", "help", "support", "positive", "safe", "protect"}
        negative_words = {"bad", "danger", "threat", "fear", "hate", "destroy", "kill", "attack"}
        words = set(re.findall(r'\b[a-z]+\b', text))
        pos = len(words & positive_words)
        neg = len(words & negative_words)
        if neg > pos:
            return "negative"
        elif pos > neg:
            return "positive"
        return "neutral"

    def _detect_language(self, text: str) -> str:
        """Detect language of text"""
        try:
            from langdetect import detect
            return detect(text)
        except Exception:
            return "en"

    def _build_summary(self, level: str, score: float, hits: dict, ml_result: dict | None = None) -> str:
        parts = [f"Threat level: {level.upper()} (score: {score:.2f})."]

        categories = list(hits.keys())
        if categories:
            parts.append(f"Rule-based indicators in: {', '.join(categories)}.")

        if ml_result and ml_result.get("method") == "ml_model":
            ml_level = ml_result.get("ml_threat_level", "")
            ml_attack = ml_result.get("ml_attack_type", "")
            if ml_level:
                parts.append(f"ML-predicted threat level: {ml_level}.")
            if ml_attack:
                parts.append(f"ML-predicted attack type: {ml_attack}.")

        if not categories and not (ml_result and ml_result.get("method") == "ml_model"):
            return "No significant threat indicators detected in the analyzed content."

        parts.append("Further manual review is recommended.")
        return " ".join(parts)

    def _empty_result(self) -> dict:
        return {
            "threat_score": 0.0,
            "threat_level": "low",
            "summary": "No content to analyze.",
            "details": {},
            "keywords": [],
            "sentiment": "neutral",
            "language": "unknown",
        }
