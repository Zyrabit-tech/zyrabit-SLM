from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from io import BytesIO

from app.main import app

client = TestClient(app)

@patch('app.domain.use_cases.chat_use_case.ChatUseCase.execute')
def test_end_to_end_rag_flow(mock_execute):
    mock_execute.return_value = {
        "response": "Robert C. Martin opina que el framework es un detalle.",
        "metadata": {"decision": "rag", "latency_ms": 100, "sources": ["clean_architecture.pdf"], "pii_detected": False, "cached": False}
    }

    query = {"text": "¿Qué opina Robert C. Martin sobre los frameworks?"}
    response = client.post("/v1/chat", json=query)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["metadata"]["decision"] == "rag"
    assert "framework" in data["response"].lower()
    mock_execute.assert_called_once()

@patch('app.domain.use_cases.chat_use_case.ChatUseCase.execute')
def test_end_to_end_direct_slm_flow(mock_execute):
    mock_execute.return_value = {
        "response": "Python es un lenguaje de programación interpretado.",
        "metadata": {"decision": "direct", "latency_ms": 50, "sources": [], "pii_detected": False, "cached": False}
    }

    query = {"text": "¿Qué es Python?"}
    response = client.post("/v1/chat", json=query)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["metadata"]["decision"] == "direct"
    assert "python" in data["response"].lower()
    mock_execute.assert_called_once()

@patch('app.domain.use_cases.chat_use_case.ChatUseCase.execute')
def test_end_to_end_reject_query_flow(mock_execute):
    mock_execute.return_value = {
        "response": "I'm sorry, that query is out of scope.",
        "metadata": {"decision": "rejected", "cached": False}
    }
    query = {"text": "comprar viagra barato ahora"}
    response = client.post("/v1/chat", json=query)
    assert response.status_code == 200
    data = response.json()
    assert "out of scope" in data["response"].lower()

@patch('app.domain.use_cases.ingest_use_case.IngestUseCase.execute')
@patch('app.domain.use_cases.chat_use_case.ChatUseCase.execute')
def test_ingest_then_query_flow(mock_chat, mock_ingest, tmp_path):
    with patch('app.api.v1.endpoints.documents.DOCS_DIR', str(tmp_path)):
        pdf_content = b"%PDF-1.4 fake clean architecture book"
        files = {"file": ("clean_architecture.pdf", BytesIO(pdf_content), "application/pdf")}
        ingest_response = client.post("/v1/ingest", files=files)
        assert ingest_response.status_code == 200
        assert ingest_response.json()["status"] == "accepted"

    mock_chat.return_value = {
        "response": "Clean Architecture propone que el framework sea un detalle.",
        "metadata": {"decision": "rag", "latency_ms": 100, "sources": ["clean_architecture.pdf"], "pii_detected": False, "cached": False}
    }
    query = {"text": "¿Qué propone Clean Architecture sobre frameworks?"}
    chat_response = client.post("/v1/chat", json=query)
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert "clean architecture" in data["response"].lower()


@patch('app.domain.use_cases.chat_use_case.ChatUseCase.execute')
def test_multiple_queries_flow(mock_execute):
    mock_execute.side_effect = [
        {"response": "Respuesta RAG 1", "metadata": {"decision": "rag", "latency_ms": 100, "sources": ["doc1.txt"], "pii_detected": False, "cached": False}},
        {"response": "Respuesta SLM 2", "metadata": {"decision": "direct", "latency_ms": 50, "sources": [], "pii_detected": False, "cached": False}},
        {"response": "Out of scope", "metadata": {"decision": "rejected", "latency_ms": 0, "sources": [], "pii_detected": False, "cached": False}}
    ]

    client.post("/v1/chat", json={"text": "Pregunta técnica 1"})
    client.post("/v1/chat", json={"text": "Pregunta general 2"})
    client.post("/v1/chat", json={"text": "spam query"})
    
    assert mock_execute.call_count == 3


@patch('app.api.v1.dependencies.get_inference_provider')
@patch('app.api.v1.dependencies.get_vector_store')
def test_health_check_before_operations(mock_get_db, mock_get_inf):
    # This might fail if the dependencies are imported differently.
    # In V5.0 health endpoint:
    response = client.get("/v1/health")
    assert response.status_code == 200


@patch('app.domain.use_cases.chat_use_case.ChatUseCase.execute')
def test_error_recovery_flow(mock_execute):
    mock_execute.return_value = {
        "response": "Lo siento, ocurrió un error",
        "metadata": {"decision": "error", "latency_ms": 100, "sources": [], "pii_detected": False, "cached": False}
    }
    response1 = client.post("/v1/chat", json={"text": "Pregunta 1"})
    assert response1.status_code == 200
    assert "error" in response1.json()["response"].lower()


def test_metrics_endpoint_exposes_prometheus_text():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
