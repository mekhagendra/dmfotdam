"""
Tests for utility functions
"""

import pytest
from app.utils.text_processor import clean_text, tokenize, extract_sentences, truncate_text


def test_clean_text():
    result = clean_text("Hello   world!!  Test@#$  text")
    assert "Hello" in result
    assert "world" in result


def test_tokenize():
    tokens = tokenize("Hello World Test")
    assert "hello" in tokens
    assert "world" in tokens


def test_extract_sentences():
    text = "First sentence. Second sentence! Third one?"
    sentences = extract_sentences(text)
    assert len(sentences) == 3


def test_truncate_text_short():
    text = "Short text"
    assert truncate_text(text, 100) == text


def test_truncate_text_long():
    text = "word " * 100
    result = truncate_text(text, 50)
    assert len(result) <= 55  # 50 + "..."
    assert result.endswith("...")
