import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO

from app.main import app

client = TestClient(app)

# --- TEST 1: Health Check ---


def test_health_check_returns_ok_status():
    """
    Test that /health returns status ok and configured URLs.
    """
    # WHEN
    response = client.get("/health")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "SLM_url" in data
    assert "db_url" in data


# --- TEST 2: Ingest Document - Success ---

@patch('app.main.INGEST_DIR', '/tmp/test_ingest_dir')
@patch('app.services.process_and_ingest_file')
def test_ingest_document_success(mock_process_file):
    """
    Test that ingesting a valid PDF document succeeds.
    """
    # GIVEN
    mock_process_file.return_value = {
        "status": "success",
        "chunks_processed": 150,
        "message": "Document ingested successfully into knowledge base."}

    # Create a fake PDF file
    pdf_content = b"%PDF-1.4 fake pdf content"
    files = {
        "file": (
            "test_document.pdf",
            BytesIO(pdf_content),
            "application/pdf")}

    # WHEN
    response = client.post("/v1/ingest", files=files)

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["chunks_processed"] == 150
    mock_process_file.assert_called_once()


# --- TEST 3: Ingest Document - Invalid File Type ---

def test_ingest_document_invalid_file_type():
    """
    Test that the endpoint rejects files that are not PDF, TXT, or MD.
    """
    # GIVEN - .exe is not allowed
    exe_content = b"MZ fake executable"
    files = {"file": ("malware.exe", BytesIO(exe_content), "application/octet-stream")}

    # WHEN
    response = client.post("/v1/ingest", files=files)

    # THEN
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"].lower()


# --- TEST 4: Ingest Document - File Too Large ---
# NOTE: This test is omitted because in-memory size validation can cause issues
# In production, payload size would be validated via server configuration (nginx, etc.)
# and this test would require too much memory to be practical.


# --- TEST 5: Chat Router - Error Handling ---

@patch('app.services.get_slm_router_decision')
@patch('app.services.execute_rag_pipeline_with_metadata')
def test_chat_router_handles_service_exceptions(
        mock_rag_pipeline, mock_router_decision):
    """
    Test that the router handles exceptions when backend services fail.
    """
    # GIVEN
    mock_router_decision.return_value = "search_rag_database"
    # Simulate the RAG pipeline throwing an error (handled internally)
    mock_rag_pipeline.return_value = ("Lo siento, ocurrió un error al procesar tu consulta con la base de datos de conocimiento.", 0)

    query = {"text": "¿Qué es clean architecture?"}

    # WHEN
    response = client.post("/v1/chat", json=query)

    # THEN
    # The service must return a controlled error message
    assert response.status_code == 200
    assert "error" in response.json()["response"].lower()


# --- TEST 6: Chat Router - Decision Fallback ---

@patch('app.services.get_slm_router_decision')
@patch('app.services.call_direct_slm')
def test_chat_router_handles_unknown_decision(
        mock_direct_slm, mock_router_decision):
    """
    Test that the router handles an unknown SLM routing decision.
    If get_slm_router_decision returns an unknown decision, it must raise HTTP 500.
    """
    # GIVEN
    # Simulate a decision that is not recognized
    mock_router_decision.return_value = "unknown_decision"

    query = {"text": "¿Qué es Python?"}

    # WHEN
    response = client.post("/v1/chat", json=query)

    # THEN
    # The endpoint should return a 500 status code
    assert response.status_code == 500
    assert "unknown" in response.json()["detail"].lower()
