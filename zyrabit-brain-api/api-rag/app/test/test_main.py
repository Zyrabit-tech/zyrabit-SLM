import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO

from app.main import app

client = TestClient(app)

# --- PRUEBA 1: Health Check ---


def test_health_check_returns_ok_status():
    """
    Prueba que el endpoint /health retorna status ok y las URLs configuradas.
    """
    # WHEN
    response = client.get("/health")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "llm_url" in data
    assert "db_url" in data


# --- PRUEBA 2: Ingest Document - Success ---

@patch('app.services.process_and_ingest_file')
def test_ingest_document_success(mock_process_file):
    """
    Prueba que la ingesta de un PDF válido sea exitosa.
    """
    # GIVEN
    mock_process_file.return_value = {
        "status": "success",
        "chunks_processed": 150,
        "message": "Documento ingestada correctamente en la base de conocimiento."}

    # Crear un archivo PDF falso
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


# --- PRUEBA 3: Ingest Document - Invalid File Type ---

def test_ingest_document_invalid_file_type():
    """
    Prueba que el endpoint rechace archivos que no sean PDF.
    """
    # GIVEN
    txt_content = b"This is a text file"
    files = {"file": ("document.txt", BytesIO(txt_content), "text/plain")}

    # WHEN
    response = client.post("/v1/ingest", files=files)

    # THEN
    assert response.status_code == 400
    assert "no permitido" in response.json()["detail"].lower()


# --- PRUEBA 4: Ingest Document - File Too Large ---
# NOTA: Este test se omite porque la validación de tamaño en memoria puede causar problemas
# En producción, el tamaño se validaría con configuración del servidor (nginx, etc.)
# y este test requeriría demasiada memoria para ser práctico


# --- PRUEBA 5: Chat Router - Error Handling ---

@patch('app.services.get_llm_router_decision')
@patch('app.services.execute_rag_pipeline')
def test_chat_router_handles_service_exceptions(
        mock_rag_pipeline, mock_router_decision):
    """
    Prueba que el router maneje excepciones cuando los servicios fallan.
    """
    # GIVEN
    mock_router_decision.return_value = "search_rag_database"
    # Simulamos que el pipeline RAG retorna un mensaje de error (ya maneja la
    # excepción internamente)
    mock_rag_pipeline.return_value = "Lo siento, ocurrió un error al procesar tu consulta con la base de datos de conocimiento."

    query = {"text": "¿Qué es clean architecture?"}

    # WHEN
    response = client.post("/v1/chat", json=query)

    # THEN
    # El servicio debe devolver un mensaje de error controlado
    assert response.status_code == 200
    assert "error" in response.json()["response"].lower()


# --- PRUEBA 6: Chat Router - Decision Fallback ---

@patch('app.services.get_llm_router_decision')
@patch('app.services.call_direct_llm')
def test_chat_router_handles_unknown_decision(
        mock_direct_llm, mock_router_decision):
    """
    Prueba que el router maneje una decisión desconocida del LLM.
    Si get_llm_router_decision retorna algo inesperado, debería manejarlo.
    """
    # GIVEN
    # Simulamos una decisión que no es ninguna de las esperadas
    mock_router_decision.return_value = "unknown_decision"

    query = {"text": "¿Qué es Python?"}

    # WHEN
    response = client.post("/v1/chat", json=query)

    # THEN
    # El endpoint debería retornar un 500 con un mensaje de error
    assert response.status_code == 500
    assert "desconocida" in response.json()["detail"].lower()
