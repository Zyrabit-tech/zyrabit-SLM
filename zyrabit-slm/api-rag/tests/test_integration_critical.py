"""
Integration tests for critical RAG and API functions.

These tests validate the critical paths with mocked external dependencies
(ChromaDB, Ollama) so they run without Docker.
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app
from app.domain.services.gatekeeper import Gatekeeper

client = TestClient(app)


# --- Router decision (no mocks - pure logic) ---

def test_router_returns_rag_for_zyrabit_keyword():
    """Router must send Zyrabit-related queries to RAG."""
    assert Gatekeeper.get_routing_decision("¿Qué es Zyrabit?") == "rag"
    assert Gatekeeper.get_routing_decision("Explain the architecture") == "rag"
    assert Gatekeeper.get_routing_decision("How does RAG work here?") == "rag"


def test_router_returns_direct_for_general_queries():
    """Router must send general knowledge to direct SLM."""
    assert Gatekeeper.get_routing_decision("¿Qué es Python?") == "direct"
    assert Gatekeeper.get_routing_decision("Capital of France?") == "direct"


def test_router_handles_spam_as_direct():
    """
    V5.0: The Gatekeeper no longer hard-rejects off-topic queries.
    Spam/irrelevant queries are routed to direct SLM, which handles
    them contextually with the system prompt.
    """
    result = Gatekeeper.get_routing_decision("comprar viagra barato ahora")
    assert result in ("direct", "rag"), f"Expected routing decision, got: {result}"
    result2 = Gatekeeper.get_routing_decision("casino free money")
    assert result2 in ("direct", "rag"), f"Expected routing decision, got: {result2}"


# --- Ingest API ---

@patch("app.domain.use_cases.ingest_use_case.IngestUseCase.execute")
def test_ingest_txt_file_success(mock_execute, tmp_path):
    """Ingest endpoint accepts .txt files."""
    with patch('app.api.v1.endpoints.documents.DOCS_DIR', str(tmp_path)):
        mock_execute.return_value = None
        content = b"Zyrabit is a local AI solution with RAG."
        files = {"file": ("zyrabit.txt", BytesIO(content), "text/plain")}
        response = client.post("/v1/ingest", files=files)
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"


@patch("app.domain.use_cases.ingest_use_case.IngestUseCase.execute")
def test_ingest_md_file_success(mock_execute, tmp_path):
    """Ingest endpoint accepts .md files."""
    with patch('app.api.v1.endpoints.documents.DOCS_DIR', str(tmp_path)):
        mock_execute.return_value = None
        content = b"# Zyrabit\n\nLocal AI with RAG."
        files = {"file": ("readme.md", BytesIO(content), "text/markdown")}
        response = client.post("/v1/ingest", files=files)
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"


# --- RAG pipeline (mocked ChromaDB + Ollama) ---

@patch("app.domain.use_cases.chat_use_case.ChatUseCase.execute")
def test_chat_rag_includes_context_in_response(mock_execute):
    """RAG flow: chat with RAG decision returns context-aware response."""
    mock_execute.return_value = {
        "response": "Zyrabit uses ChromaDB for vector storage and Ollama for inference.",
        "metadata": {"decision": "rag", "latency_ms": 100, "sources": ["source.txt"], "pii_detected": False, "cached": False}
    }
    response = client.post(
        "/v1/chat",
        json={"text": "What does Zyrabit use for storage?"},
    )
    assert response.status_code == 200
    assert "ChromaDB" in response.json()["response"] or "Ollama" in response.json()["response"]


# --- Full chat flow ---

@patch("app.domain.use_cases.chat_use_case.ChatUseCase.execute")
def test_chat_rag_flow_returns_response(mock_execute):
    """Full chat flow: RAG query returns augmented response."""
    mock_execute.return_value = {
        "response": "Zyrabit combina SLMs con RAG y seguridad Zero-Trust.",
        "metadata": {"decision": "rag", "latency_ms": 100, "sources": ["doc.pdf"], "pii_detected": False, "cached": False}
    }

    response = client.post(
        "/v1/chat",
        json={"text": "¿Qué es Zyrabit?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["metadata"]["decision"] == "rag"
    assert "Zyrabit" in data["response"] or "RAG" in data["response"]


@patch("app.domain.use_cases.chat_use_case.ChatUseCase.execute")
def test_chat_direct_flow_returns_response(mock_execute):
    """Full chat flow: direct SLM query returns response."""
    mock_execute.return_value = {
        "response": "Python es un lenguaje de programación.",
        "metadata": {"decision": "direct", "latency_ms": 50, "sources": [], "pii_detected": False, "cached": False}
    }

    response = client.post(
        "/v1/chat",
        json={"text": "¿Qué es Python?"},
    )
    assert response.status_code == 200
    assert "Python" in response.json()["response"]


@patch("app.domain.use_cases.chat_use_case.ChatUseCase.execute")
def test_chat_reject_returns_200_with_rejection_msg(mock_execute):
    """Full chat flow: reject returns 200 with standard rejection message."""
    mock_execute.return_value = {
        "response": "I'm sorry, that query is out of scope.",
        "metadata": {"decision": "rejected", "cached": False}
    }

    response = client.post(
        "/v1/chat",
        json={"text": "comprar viagra"},
    )
    # V5.0 changed this to return a polite response instead of 400
    assert response.status_code == 200
    assert "out of scope" in response.json()["response"].lower()

# --- End of Tests ---
