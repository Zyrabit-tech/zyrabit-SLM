from fastapi.testclient import TestClient
from unittest.mock import patch
from io import BytesIO

from app.main import app

client = TestClient(app)

@patch('app.services.execute_rag_pipeline_with_metadata')
@patch('app.services.get_slm_router_decision')
def test_end_to_end_rag_flow(mock_router_decision, mock_rag_pipeline):
    mock_router_decision.return_value = "search_rag_database"
    mock_rag_pipeline.return_value = (
        "Robert C. Martin opina que el framework es un detalle que debe vivir en la capa externa según Clean Architecture.",
        2,
    )

    query = {"text": "¿Qué opina Robert C. Martin sobre los frameworks?"}
    response = client.post("/v1/chat", json=query)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["metadata"]["route_decision"] == "search_rag_database"
    assert "framework" in data["response"].lower()
    assert "clean architecture" in data["response"].lower()
    mock_router_decision.assert_called_once_with(query["text"])
    mock_rag_pipeline.assert_called_once_with(query["text"])


@patch('app.services.call_direct_slm')
@patch('app.services.get_slm_router_decision')
def test_end_to_end_direct_slm_flow(mock_router_decision, mock_direct_slm):
    mock_router_decision.return_value = "direct_SLM_answer"
    mock_direct_slm.return_value = "Python es un lenguaje de programación interpretado, de alto nivel y de propósito general."

    query = {"text": "¿Qué es Python?"}
    response = client.post("/v1/chat", json=query)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["metadata"]["route_decision"] == "direct_SLM_answer"
    assert "python" in data["response"].lower()
    assert "lenguaje" in data["response"].lower()
    mock_router_decision.assert_called_once_with(query["text"])
    mock_direct_slm.assert_called_once_with(query["text"])


@patch('app.services.get_slm_router_decision')
def test_end_to_end_reject_query_flow(mock_router_decision):
    mock_router_decision.return_value = "reject_query"
    query = {"text": "comprar viagra barato ahora"}
    response = client.post("/v1/chat", json=query)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "fuera de alcance" in data["detail"].lower()
    mock_router_decision.assert_called_once_with(query["text"])

@patch('app.services.execute_rag_pipeline_with_metadata')
@patch('app.services.get_slm_router_decision')
@patch('app.services.process_and_ingest_file')
def test_ingest_then_query_flow(
        mock_process_file,
        mock_router_decision,
        mock_rag_pipeline,
        tmp_path):
    with patch('app.main.INGEST_DIR', str(tmp_path)):
        mock_process_file.return_value = {
            "status": "success",
            "filename": "clean_architecture.pdf",
            "ingest_id": "abc123",
            "chunks_processed": 50,
            "message": "Documento ingestado correctamente en la base de conocimiento."}

        pdf_content = b"%PDF-1.4 fake clean architecture book"
        files = {
            "file": (
                "clean_architecture.pdf",
                BytesIO(pdf_content),
                "application/pdf")
        }
        ingest_response = client.post("/v1/ingest", files=files)
        assert ingest_response.status_code == 200
        assert ingest_response.json()["status"] == "success"
        assert "ingest_id" in ingest_response.json()

    mock_router_decision.return_value = "search_rag_database"
    mock_rag_pipeline.return_value = (
        "Clean Architecture propone que el framework sea un detalle.",
        1,
    )
    query = {"text": "¿Qué propone Clean Architecture sobre frameworks?"}
    chat_response = client.post("/v1/chat", json=query)
    assert chat_response.status_code == 200
    data = chat_response.json()
    assert "clean architecture" in data["response"].lower()
    assert "framework" in data["response"].lower()


@patch('app.services.call_direct_slm')
@patch('app.services.execute_rag_pipeline_with_metadata')
@patch('app.services.get_slm_router_decision')
def test_multiple_queries_flow(
        mock_router_decision,
        mock_rag_pipeline,
        mock_direct_slm):
    mock_router_decision.return_value = "search_rag_database"
    mock_rag_pipeline.return_value = ("Respuesta RAG 1", 1)
    response1 = client.post("/v1/chat", json={"text": "Pregunta técnica 1"})
    assert response1.status_code == 200

    mock_router_decision.return_value = "direct_SLM_answer"
    mock_direct_slm.return_value = "Respuesta SLM 2"
    response2 = client.post("/v1/chat", json={"text": "Pregunta general 2"})
    assert response2.status_code == 200

    mock_router_decision.return_value = "reject_query"
    response3 = client.post("/v1/chat", json={"text": "spam query"})
    assert response3.status_code == 400

    assert mock_router_decision.call_count == 3
    mock_rag_pipeline.assert_called_once()
    mock_direct_slm.assert_called_once()


def test_health_check_before_operations():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@patch('app.services.execute_rag_pipeline_with_metadata')
@patch('app.services.call_direct_slm')
@patch('app.services.get_slm_router_decision')
def test_error_recovery_flow(
        mock_router_decision,
        mock_direct_slm,
        mock_rag_pipeline):
    mock_router_decision.return_value = "search_rag_database"
    mock_rag_pipeline.return_value = (
        "Lo siento, ocurrió un error al procesar tu consulta con la base de datos de conocimiento.",
        0,
    )
    response1 = client.post("/v1/chat", json={"text": "Pregunta 1"})
    assert response1.status_code == 200
    assert "error" in response1.json()["response"].lower()

    mock_router_decision.return_value = "direct_SLM_answer"
    mock_direct_slm.return_value = "Respuesta correcta"
    response2 = client.post("/v1/chat", json={"text": "Pregunta 2"})
    assert response2.status_code == 200
    assert "Respuesta correcta" in response2.json()["response"]

def test_metrics_endpoint_exposes_prometheus_text():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "zyrabit_token_usage_total" in body
    assert "http_requests_total" in body
