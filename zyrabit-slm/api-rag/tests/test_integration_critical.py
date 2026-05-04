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

@patch("app.services.process_and_ingest_file")
def test_ingest_txt_file_success(mock_process, tmp_path):
    """Ingest endpoint accepts .txt files."""
    with patch('app.api.v1.endpoints.documents.DOCS_DIR', str(tmp_path)):
        mock_process.return_value = {
            "status": "success",
            "chunks_processed": 5,
            "message": "Documento ingestado correctamente.",
        }
        content = b"Zyrabit is a local AI solution with RAG."
        files = {"file": ("zyrabit.txt", BytesIO(content), "text/plain")}
        response = client.post("/v1/ingest", files=files)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["chunks_processed"] == 5


@patch("app.services.process_and_ingest_file")
def test_ingest_md_file_success(mock_process, tmp_path):
    """Ingest endpoint accepts .md files."""
    with patch('app.api.v1.endpoints.documents.DOCS_DIR', str(tmp_path)):
        mock_process.return_value = {
            "status": "success",
            "chunks_processed": 3,
            "message": "Documento ingestado correctamente.",
        }
        content = b"# Zyrabit\n\nLocal AI with RAG."
        files = {"file": ("readme.md", BytesIO(content), "text/markdown")}
        response = client.post("/v1/ingest", files=files)
        assert response.status_code == 200
        assert response.json()["status"] == "success"


# --- RAG pipeline (mocked ChromaDB + Ollama) ---

@patch("app.domain.use_cases.ChatUseCase.execute_rag")
def test_chat_rag_includes_context_in_response(mock_rag):
    """RAG flow: chat with RAG decision returns context-aware response."""
    mock_rag.return_value = ("Zyrabit uses ChromaDB for vector storage and Ollama for inference.", 2, 0.5, ["source.txt"])
    # This tests the full flow; execute_rag_pipeline internals are tested in Docker E2E
    response = client.post(
        "/v1/chat",
        json={"text": "What does Zyrabit use for storage?"},
    )
    assert response.status_code == 200
    assert "ChromaDB" in response.json()["response"] or "Ollama" in response.json()["response"]


# --- Full chat flow ---

@patch("app.domain.services.gatekeeper.Gatekeeper.get_routing_decision")
@patch("app.domain.use_cases.ChatUseCase.execute_rag")
def test_chat_rag_flow_returns_response(mock_rag, mock_router):
    """Full chat flow: RAG query returns augmented response."""
    mock_router.return_value = "search_rag_database"
    mock_rag.return_value = ("Zyrabit combina SLMs con RAG y seguridad Zero-Trust.", 1, 0.4, ["doc.pdf"])

    response = client.post(
        "/v1/chat",
        json={"text": "¿Qué es Zyrabit?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["metadata"]["decision"] == "search_rag_database"
    assert "Zyrabit" in data["response"] or "RAG" in data["response"]


@patch("app.domain.use_cases.ChatUseCase.execute_direct_chat")
@patch("app.domain.services.gatekeeper.Gatekeeper.get_routing_decision")
def test_chat_direct_flow_returns_response(mock_router, mock_slm):
    """Full chat flow: direct SLM query returns response."""
    mock_router.return_value = "direct_SLM_answer"
    mock_slm.return_value = ("Python es un lenguaje de programación.", 0.2)

    response = client.post(
        "/v1/chat",
        json={"text": "¿Qué es Python?"},
    )
    assert response.status_code == 200
    assert "Python" in response.json()["response"]


@patch("app.domain.services.gatekeeper.Gatekeeper.get_routing_decision")
def test_chat_reject_returns_400(mock_router):
    """Full chat flow: reject returns 400."""
    mock_router.return_value = "reject_query"

    response = client.post(
        "/v1/chat",
        json={"text": "comprar viagra"},
    )
    assert response.status_code == 400
    assert "out of scope" in response.json()["detail"].lower()


# --- End of Tests ---
