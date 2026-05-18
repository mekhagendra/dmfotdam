"""
Tests for the text analyzer service
"""

import pytest
from app.services.text_analyzer import TextAnalyzer


@pytest.fixture
def analyzer():
    return TextAnalyzer()


@pytest.mark.asyncio
async def test_analyze_empty_text(analyzer):
    result = await analyzer.analyze("")
    assert result["threat_score"] == 0.0
    assert result["threat_level"] == "low"


@pytest.mark.asyncio
async def test_analyze_normal_text(analyzer):
    text = "The weather today is beautiful and the sun is shining. People are enjoying the park."
    result = await analyzer.analyze(text)
    assert result["threat_score"] < 0.3
    assert result["threat_level"] == "low"
    assert result["sentiment"] is None or result["sentiment"] in ("positive", "neutral", "negative")


@pytest.mark.asyncio
async def test_analyze_threat_keywords(analyzer):
    """Keywords and result structure are correct; score depends on the active model."""
    text = (
        "The attack was planned with explosive devices. "
        "The militant group coordinated the operation to target infrastructure. "
        "Funding for the attack came through money laundering channels."
    )
    result = await analyzer.analyze(text)
    assert isinstance(result["threat_score"], float)
    assert result["threat_level"] in ("low", "medium", "high", "critical")
    assert len(result["keywords"]) > 0


@pytest.mark.asyncio
async def test_analyze_returns_keywords(analyzer):
    text = "Security analysis of the document reveals several indicators related to suspicious activity."
    result = await analyzer.analyze(text)
    assert isinstance(result["keywords"], list)


def test_score_to_level(analyzer):
    assert analyzer._score_to_level(0.1) == "low"
    assert analyzer._score_to_level(0.3) == "medium"
    assert analyzer._score_to_level(0.5) == "medium"
    assert analyzer._score_to_level(0.61) == "high"
    assert analyzer._score_to_level(0.85) == "critical"


def test_extract_text_from_txt(analyzer, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("This is a test document for analysis.")
    result = analyzer.extract_text_from_file(str(test_file), "txt")
    assert "test document" in result
