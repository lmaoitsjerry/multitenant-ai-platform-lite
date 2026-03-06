"""
Test 3b: Live Helpdesk RAG — Private KB Content Integration

NOTE: This test requires:
  1. A running backend with the Round 6 code DEPLOYED
  2. The KB document (Main Essay Pt. 1.docx) UPLOADED and INDEXED

Run manually: python -m pytest tests/test_helpdesk_live.py -v --tb=long -s

Current status: The deployed service has 0 private KB documents indexed.
These tests will xfail until the document is uploaded and code is deployed.
"""
import os
import pytest

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

BASE_URL = os.getenv("API_BASE_URL", "https://ht-itc-lite-1031318281967.africa-south1.run.app")


def get_auth_token():
    """Get auth token for API calls."""
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": "demo@africastay.com",
            "password": "Test123!"
        }, timeout=15)
        return response.json().get("access_token")
    except Exception:
        return None


def ask_helpdesk(question: str, token: str) -> dict:
    """Send a question to the helpdesk and return the response."""
    response = requests.post(
        f"{BASE_URL}/api/v1/helpdesk/ask",
        json={"question": question, "session_id": "test-round6-rag"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    return response.json()


@pytest.fixture(scope="module")
def auth_token():
    if not HAS_REQUESTS:
        pytest.skip("requests library not available")
    token = get_auth_token()
    if not token:
        pytest.skip("Could not authenticate — skipping live test")
    return token


@pytest.fixture(scope="module")
def kb_has_documents(auth_token):
    """Check if private KB has any indexed documents."""
    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/knowledge/documents",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=15,
        )
        data = r.json()
        count = data.get("count", 0)
        if count == 0:
            pytest.skip("Private KB has 0 documents — upload Main Essay Pt. 1.docx first")
        return True
    except Exception as e:
        pytest.skip(f"Could not check KB documents: {e}")


@pytest.mark.xfail(reason="Requires deployed code + indexed KB document", strict=False)
def test_helpdesk_answers_bates_question(auth_token):
    """
    The Main Essay Pt. 1.docx contains an essay about Bates and McDoom on Rwanda.
    Helpdesk should answer using its content, not return a fallback.
    """
    result = ask_helpdesk(
        "What does Robert Bates claim about Rwanda's multi-party elections?",
        auth_token
    )
    answer = result.get("answer", "")
    print(f"\nQ1: What does Robert Bates claim about Rwanda's multi-party elections?")
    print(f"Answer: {answer[:300]}")
    print(f"Confidence: {result.get('confidence', 'N/A')}")
    print(f"Method: {result.get('method', 'N/A')}")
    print(f"Sources: {result.get('sources', [])}")

    lower = answer.lower()
    # Should mention elections, violence, or related concepts
    assert any(word in lower for word in ["election", "violence", "escalat", "ethnic", "bates"]), \
        f"Expected answer about elections/violence, got: {answer[:200]}"


@pytest.mark.xfail(reason="Requires deployed code + indexed KB document", strict=False)
def test_helpdesk_compares_bates_mcdoom(auth_token):
    """Should explain differences between Bates and McDoom, not return fallback."""
    result = ask_helpdesk(
        "What are the key differences between Bates and McDoom on the Rwandan genocide?",
        auth_token
    )
    answer = result.get("answer", "")
    print(f"\nQ2: Bates vs McDoom differences?")
    print(f"Answer: {answer[:300]}")
    print(f"Confidence: {result.get('confidence', 'N/A')}")

    lower = answer.lower()
    assert "couldn't find" not in lower, "Helpdesk returned fallback instead of using KB content"
    assert "could not find" not in lower, "Helpdesk returned fallback"
    assert "bates" in lower or "mcdoom" in lower, \
        f"Expected mention of Bates/McDoom, got: {answer[:200]}"


@pytest.mark.xfail(reason="Requires deployed code + indexed KB document", strict=False)
def test_helpdesk_book_title(auth_token):
    """Should identify Bates' book title."""
    result = ask_helpdesk(
        "What book did Robert Bates write about state failure?",
        auth_token
    )
    answer = result.get("answer", "")
    print(f"\nQ3: Bates' book title?")
    print(f"Answer: {answer[:300]}")

    lower = answer.lower()
    assert "fell apart" in lower or "state failure" in lower or "africa" in lower or "bates" in lower, \
        f"Expected book title reference, got: {answer[:200]}"


def test_helpdesk_travel_ignores_essay(auth_token):
    """Travel question should NOT cite the genocide essay."""
    try:
        result = ask_helpdesk(
            "What hotels are available in Zanzibar?",
            auth_token
        )
    except Exception as e:
        pytest.skip(f"Live service timeout/error: {e}")

    answer = result.get("answer", "")
    print(f"\nQ4: Hotels in Zanzibar?")
    print(f"Answer: {answer[:300]}")

    lower = answer.lower()
    assert "bates" not in lower, "Travel question incorrectly used essay content"
    assert "genocide" not in lower, "Travel question incorrectly used essay content"
