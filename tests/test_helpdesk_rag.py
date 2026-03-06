"""Test 3: Helpdesk RAG — Private KB Content Integration"""
import pytest


def test_low_quality_answer_detection():
    """_is_low_quality_answer should detect fallback phrases."""
    from src.api.helpdesk_routes import _is_low_quality_answer

    # Low quality — fallback phrases
    assert _is_low_quality_answer(
        "I couldn't find specific information about that in my knowledge base.", 0.8
    ) is True

    assert _is_low_quality_answer(
        "I don't have information about the Rwandan genocide.", 0.9
    ) is True

    assert _is_low_quality_answer(
        "I could not find relevant details.", 0.85
    ) is True

    assert _is_low_quality_answer(
        "That's not available in my knowledge base.", 0.7
    ) is True

    # Low quality — low confidence regardless of answer text
    assert _is_low_quality_answer(
        "The Rwandan genocide occurred in 1994.", 0.3
    ) is True

    assert _is_low_quality_answer(
        "Some reasonable answer.", 0.49
    ) is True

    # High quality — real answer with good confidence
    assert _is_low_quality_answer(
        "According to Bates, Rwanda's multi-party elections escalated violence.", 0.85
    ) is False

    # High quality — travel answer
    assert _is_low_quality_answer(
        "The best time to visit Zanzibar is June to October.", 0.9
    ) is False


def test_low_quality_phrases_list():
    """Verify the LOW_QUALITY_PHRASES list is loaded and non-empty."""
    from src.api.helpdesk_routes import _LOW_QUALITY_PHRASES

    assert len(_LOW_QUALITY_PHRASES) >= 5, "Should have at least 5 fallback phrases"
    assert "couldn't find" in _LOW_QUALITY_PHRASES
    assert "could not find" in _LOW_QUALITY_PHRASES
    assert "don't have" in _LOW_QUALITY_PHRASES


def test_confidence_boundary():
    """Test the 0.5 confidence boundary."""
    from src.api.helpdesk_routes import _is_low_quality_answer

    # Exactly 0.5 should NOT be low quality (only < 0.5 triggers)
    assert _is_low_quality_answer("Good answer.", 0.5) is False
    # Just below should be low quality
    assert _is_low_quality_answer("Good answer.", 0.499) is True


def test_high_confidence_with_no_fallback_phrase():
    """High confidence + no fallback phrase = good answer."""
    from src.api.helpdesk_routes import _is_low_quality_answer

    assert _is_low_quality_answer(
        "Zanzibar has beautiful white sand beaches.", 0.92
    ) is False


def test_private_kb_detection_logic():
    """Simulate the private KB detection guard logic."""
    citations = [
        {"source_type": "global_kb", "score": 0.8, "source": "hotels.json"},
        {"source_type": "private_kb", "score": 0.65, "source": "Main Essay Pt. 1.docx"},
    ]

    has_private_kb = any(
        c.get("source_type") == "private_kb" and c.get("score", 0) >= 0.4
        for c in citations
    )
    assert has_private_kb is True, "Should detect private KB result with score >= 0.4"


def test_no_private_kb_when_low_score():
    """Private KB results below 0.4 should not trigger fallthrough."""
    citations = [
        {"source_type": "global_kb", "score": 0.8, "source": "hotels.json"},
        {"source_type": "private_kb", "score": 0.2, "source": "Irrelevant.pdf"},
    ]

    has_private_kb = any(
        c.get("source_type") == "private_kb" and c.get("score", 0) >= 0.4
        for c in citations
    )
    assert has_private_kb is False, "Low-score private KB should not trigger"
