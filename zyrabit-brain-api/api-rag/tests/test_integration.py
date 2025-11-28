import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from io import BytesIO

from app.main import app

client = TestClient(app)

# --- PRUEBA 1: End-to-End RAG Flow ---


@patch('app.services.execute_rag_pipeline')
@patch('app.services.get_llm_router_decision')
def test_end_to_end_rag_flow(mock_router_decision, mock_rag_pipeline):
    """
    Prueba el flujo completo: Usuario pregunta → Router → RAG → Respuesta.
    """
    # GIVEN
    mock_router_decision.return_value = "search_rag_database"
    mock_rag_pipeline.return_value = "Robert C. Martin opina que el framework es un detalle que debe vivir en la capa externa según Clean Architecture."

    query = {"text": "¿Qué opina Robert C. Martin sobre los frameworks?"}

    # WHEN
    response = client.post("/v1/chat", json=query)

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "framework" in data["response"].lower()
    assert "detalle" in data["response"].lower()

    # Verificar que se llamó a los servicios correctos
    mock_router_decision.assert_called_once_with(query["text"])
    mock_rag_pipeline.assert_called_once_with(query["text"])

# --- PRUEBA 2: End-to-End Direct LLM Flow ---


@patch('app.services.call_direct_llm')
@patch('app.services.get_llm_router_decision')
def test_end_to_end_direct_llm_flow(mock_router_decision, mock_direct_llm):
    """
    Prueba el flujo completo: Usuario pregunta → Router → LLM Directo → Respuesta.
    """
    # GIVEN
    mock_router_decision.return_value = "direct_llm_answer"
    mock_direct_llm.return_value = "Python es un lenguaje de programación interpretado, de alto nivel y de propósito general."

    query = {"text": "¿Qué es Python?"}

    # WHEN
    response = client.post("/v1/chat", json=query)

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "python" in data["response"].lower()
    assert "lenguaje" in data["response"].lower()

    # Verificar que se llamó a los servicios correctos
    mock_router_decision.assert_called_once_with(query["text"])
    mock_direct_llm.assert_called_once_with(query["text"])

# --- PRUEBA 3: End-to-End Reject Query Flow ---


@patch('app.services.get_llm_router_decision')
def test_end_to_end_reject_query_flow(mock_router_decision):
    """
    Prueba el flujo completo: Usuario pregunta spam → Router → Rechazo.
    """
    # GIVEN
    mock_router_decision.return_value = "reject_query"

    query = {"text": "comprar viagra barato ahora"}

    # WHEN
    response = client.post("/v1/chat", json=query)

    # THEN
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "fuera de alcance" in data["detail"].lower()

    # Verificar que se llamó al router
    mock_router_decision.assert_called_once_with(query["text"])

# --- PRUEBA 4: Ingest Then Query Flow ---


@patch('app.services.execute_rag_pipeline')
@patch('app.services.get_llm_router_decision')
@patch('app.services.process_and_ingest_file')
def test_ingest_then_query_flow(
        mock_process_file,
        mock_router_decision,
        mock_rag_pipeline):
    """
    Prueba el flujo: Ingesta PDF → Consulta sobre el contenido → Respuesta RAG.
    """
    # PARTE 1: INGESTA
    # GIVEN
    mock_process_file.return_value = {
        "status": "success",
        "chunks_processed": 50,
        "message": "Documento ingestada correctamente en la base de conocimiento."}

    pdf_content = b"%PDF-1.4 fake clean architecture book"
    files = {
        "file": (
            "clean_architecture.pdf",
            BytesIO(pdf_content),
            "application/pdf")}

    # WHEN
    ingest_response = client.post("/v1/ingest", files=files)

    # THEN
    assert ingest_response.status_code == 200
    assert ingest_response.json()["status"] == "success"

    # PARTE 2: CONSULTA
    # GIVEN
    mock_router_decision.return_value = "search_rag_database"
    mock_rag_pipeline.return_value = "Clean Architecture propone que el framework sea un detalle."

    query = {"text": "¿Qué propone Clean Architecture sobre frameworks?"}

    # WHEN
    chat_response = client.post("/v1/chat", json=query)

    # THEN
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert "clean architecture" in data["response"].lower()
    assert "framework" in data["response"].lower()

# --- PRUEBA 5: Multiple Queries Flow ---


@patch('app.services.call_direct_llm')
@patch('app.services.execute_rag_pipeline')
@patch('app.services.get_llm_router_decision')
def test_multiple_queries_flow(
        mock_router_decision,
        mock_rag_pipeline,
        mock_direct_llm):
    """
    Prueba múltiples consultas en secuencia con diferentes rutas.
    """
    # Query 1: RAG
    mock_router_decision.return_value = "search_rag_database"
    mock_rag_pipeline.return_value = "Respuesta RAG 1"

    response1 = client.post("/v1/chat", json={"text": "Pregunta técnica 1"})
    assert response1.status_code == 200

    # Query 2: Direct LLM
    mock_router_decision.return_value = "direct_llm_answer"
    mock_direct_llm.return_value = "Respuesta LLM 2"

    response2 = client.post("/v1/chat", json={"text": "Pregunta general 2"})
    assert response2.status_code == 200

    # Query 3: Reject
    mock_router_decision.return_value = "reject_query"

    response3 = client.post("/v1/chat", json={"text": "spam query"})
    assert response3.status_code == 400

    # Verificar que todas las consultas funcionaron independientemente
    assert mock_router_decision.call_count == 3
    mock_rag_pipeline.assert_called_once()
    mock_direct_llm.assert_called_once()

# --- PRUEBA 6: Health Check Before Operations ---


def test_health_check_before_operations():
    """
    Prueba que el health check funcione antes de realizar operaciones.
    """
    # WHEN
    response = client.get("/health")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

    # Esto simula verificar que el sistema esté listo antes de operaciones
    if data["status"] == "ok":
        # Entonces podemos hacer consultas
        pass

# --- PRUEBA 7: Error Recovery Flow ---


@patch('app.services.execute_rag_pipeline')
@patch('app.services.call_direct_llm')
@patch('app.services.get_llm_router_decision')
def test_error_recovery_flow(
        mock_router_decision,
        mock_direct_llm,
        mock_rag_pipeline):
    """
    Prueba que el sistema se recupere de errores y siga funcionando.
    """
    # Query 1: RAG falla
    mock_router_decision.return_value = "search_rag_database"
    mock_rag_pipeline.return_value = "Lo siento, ocurrió un error al procesar tu consulta con la base de datos de conocimiento."

    response1 = client.post("/v1/chat", json={"text": "Pregunta 1"})
    assert response1.status_code == 200
    assert "error" in response1.json()["response"].lower()

    # Query 2: Direct LLM funciona bien
    mock_router_decision.return_value = "direct_llm_answer"
    mock_direct_llm.return_value = "Respuesta correcta"

    response2 = client.post("/v1/chat", json={"text": "Pregunta 2"})
    assert response2.status_code == 200
    assert "Respuesta correcta" in response2.json()["response"]

    # El sistema se recuperó exitosamente
