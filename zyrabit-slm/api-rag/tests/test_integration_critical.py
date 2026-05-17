import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from fastapi.testclient import TestClient
from app.domain.services.gatekeeper import Gatekeeper

from app.domain.services.gatekeeper import Gatekeeper

def test_router_returns_rag_for_zyrabit_keyword():
    assert Gatekeeper.get_routing_decision("¿Qué es Zyrabit?") == "rag"

def test_router_returns_direct_for_general_queries():
    assert Gatekeeper.get_routing_decision("¿Qué es Python?") == "direct"

@patch("app.domain.use_cases.ingest_use_case.IngestUseCase.execute")
def test_ingest_txt_file_success(mock_execute, client, tmp_path):
    with patch('app.api.v1.endpoints.documents.DOCS_DIR', str(tmp_path)):
        mock_execute.return_value = None
        content = b"Zyrabit is a local AI solution with RAG."
        files = {"file": ("zyrabit.txt", BytesIO(content), "text/plain")}
        response = client.post("/v1/ingest", files=files)
        assert response.status_code == 200

@patch("app.domain.use_cases.ingest_use_case.IngestUseCase.execute")
def test_ingest_md_file_success(mock_execute, client, tmp_path):
    with patch('app.api.v1.endpoints.documents.DOCS_DIR', str(tmp_path)):
        mock_execute.return_value = None
        content = b"# Zyrabit\n\nLocal AI with RAG."
        files = {"file": ("readme.md", BytesIO(content), "text/markdown")}
        response = client.post("/v1/ingest", files=files)
        assert response.status_code == 200

@patch("app.domain.use_cases.chat_use_case.ChatUseCase.execute")
def test_chat_rag_includes_context_in_response(mock_execute, client):
    mock_execute.return_value = {
        "response": "Zyrabit uses ChromaDB for vector storage and Ollama for inference.",
        "metadata": {"decision": "rag", "latency_ms": 100, "sources": ["source.txt"], "pii_detected": False, "cached": False}
    }
    response = client.post("/v1/chat", json={"text": "What does Zyrabit use for storage?"})
    assert response.status_code == 200

@patch("app.domain.use_cases.chat_use_case.ChatUseCase.execute")
def test_chat_rag_flow_returns_response(mock_execute, client):
    mock_execute.return_value = {
        "response": "Zyrabit combina SLMs con RAG y seguridad Zero-Trust.",
        "metadata": {"decision": "rag", "latency_ms": 100, "sources": ["doc.pdf"], "pii_detected": False, "cached": False}
    }
    response = client.post("/v1/chat", json={"text": "¿Qué es Zyrabit?"})
    assert response.status_code == 200

@patch("app.domain.use_cases.chat_use_case.ChatUseCase.execute")
def test_chat_direct_flow_returns_response(mock_execute, client):
    mock_execute.return_value = {
        "response": "Python es un lenguaje de programación.",
        "metadata": {"decision": "direct", "latency_ms": 50, "sources": [], "pii_detected": False, "cached": False}
    }
    response = client.post("/v1/chat", json={"text": "¿Qué es Python?"})
    assert response.status_code == 200

@patch("app.domain.use_cases.chat_use_case.ChatUseCase.execute")
def test_chat_reject_returns_200_with_rejection_msg(mock_execute, client):
    mock_execute.return_value = {
        "response": "I'm sorry, that query is out of scope.",
        "metadata": {"decision": "rejected", "cached": False}
    }
    response = client.post("/v1/chat", json={"text": "comprar viagra"})
    assert response.status_code == 200
