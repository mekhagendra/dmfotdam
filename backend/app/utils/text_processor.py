"""
Text processing utilities
"""

import re
from typing import List


def clean_text(text: str) -> str:
    """Remove special characters and normalize whitespace"""
    text = re.sub(r'[^\w\s.,!?;:\'-]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def tokenize(text: str) -> List[str]:
    """Simple word tokenization"""
    return re.findall(r'\b\w+\b', text.lower())


def extract_sentences(text: str) -> List[str]:
    """Split text into sentences"""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def truncate_text(text: str, max_length: int = 5000) -> str:
    """Truncate text to a maximum length at a word boundary"""
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."
