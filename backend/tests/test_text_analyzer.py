"""
Tests for the text analyzer service
"""

import pytest
from app.services.text_analyzer import TextAnalyzer


@pytest.fixture
def analyzer():
    return TextAnalyzer()


def test_analyze_empty_text(analyzer):
    result = analyzer.analyze("")
    assert result["threat_score"] == 0.0
    assert result["threat_level"] == "low"


def test_analyze_normal_text(analyzer):
    text = "The weather today is beautiful and the sun is shining. People are enjoying the park."
    result = analyzer.analyze(text)
    assert result["threat_score"] < 0.3
    assert result["threat_level"] == "low"
    assert result["sentiment"] in ("positive", "neutral", "negative")


def test_analyze_threat_keywords(analyzer):
    text = (
        "The attack was planned with explosive devices. "
        "The militant group coordinated the operation to target infrastructure. "
        "Funding for the attack came through money laundering channels."
    )
    result = analyzer.analyze(text)
    assert result["threat_score"] > 0.3
    assert result["threat_level"] in ("medium", "high", "critical")
    assert len(result["details"]["keyword_hits"]) > 0


def test_analyze_returns_keywords(analyzer):
    text = "Security analysis of the document reveals several indicators related to suspicious activity."
    result = analyzer.analyze(text)
    assert isinstance(result["keywords"], list)


def test_score_to_level(analyzer):
    assert analyzer._score_to_level(0.1) == "low"
    assert analyzer._score_to_level(0.3) == "medium"
    assert analyzer._score_to_level(0.5) == "high"
    assert analyzer._score_to_level(0.8) == "critical"


def test_extract_text_from_txt(analyzer, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("This is a test document for analysis.")
    result = analyzer.extract_text_from_file(str(test_file), "txt")
    assert "test document" in result
