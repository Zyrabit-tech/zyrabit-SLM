import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Ahora sí podemos importar la app
from app.main import app

client = TestClient(app)

# --- PRUEBA 1: El Router sabe cuándo usar RAG ---


@patch('app.services.execute_rag_pipeline')
@patch('app.services.get_SLM_router_decision')
def test_router_sends_tech_queries_to_RAG(
        mock_router_decision, mock_rag_pipeline):
    """
    Prueba que una pregunta sobre Robert C. Martin sea enrutada a 'search_rag_database'.
    """
    # 1. GIVEN
    mock_router_decision.return_value = "search_rag_database"
    mock_rag_pipeline.return_value = "[Respuesta RAG para: ¿Qué opina Robert C. Martin sobre los frameworks?]"

    query = {"text": "¿Qué opina Robert C. Martin sobre los frameworks?"}

    # 2. WHEN
    response = client.post("/v1/chat", json=query)

    # 3. THEN
    mock_router_decision.assert_called_once_with(query['text'])
    mock_rag_pipeline.assert_called_once_with(query['text'])

    assert response.status_code == 200
    assert "Respuesta RAG para" in response.json()['response']

# --- PRUEBA 2: El Router sabe cuándo NO usar RAG (Conocimiento General) ---


@patch('app.services.call_direct_SLM')
@patch('app.services.execute_rag_pipeline')
@patch('app.services.get_SLM_router_decision')
def test_router_sends_general_queries_to_DIRECT_SLM(
        mock_router_decision, mock_rag_pipeline, mock_direct_SLM):
    """
    Prueba que una pregunta sobre el clima sea enrutada a 'direct_SLM_answer'.
    """
    # 1. GIVEN
    mock_router_decision.return_value = "direct_SLM_answer"
    mock_direct_SLM.return_value = "[Respuesta SLM Directa para: ¿Cómo estará el clima mañana?]"

    query = {"text": "¿Cómo estará el clima mañana?"}

    # 2. WHEN
    response = client.post("/v1/chat", json=query)

    # 3. THEN
    mock_router_decision.assert_called_once_with(query['text'])
    mock_rag_pipeline.assert_not_called()
    mock_direct_SLM.assert_called_once_with(query['text'])

    assert response.status_code == 200
    assert "Respuesta SLM Directa para" in response.json()['response']

# --- PRUEBA 3: El Router sabe cuándo RECHAZAR (El Guardrail) ---


@patch('app.services.execute_rag_pipeline')
@patch('app.services.get_SLM_router_decision')
def test_router_REJECTS_out_of_scope_queries(
        mock_router_decision, mock_rag_pipeline):
    """
    Prueba que el router rechaza consultas fuera de alcance.
    """
    # 1. GIVEN
    mock_router_decision.return_value = "reject_query"
    query = {"text": "comprar viagra barato ahora"}

    # 2. WHEN
    response = client.post("/v1/chat", json=query)

    # 3. THEN
    mock_router_decision.assert_called_once_with(query['text'])
    mock_rag_pipeline.assert_not_called()

    assert response.status_code == 400
    assert "Consulta fuera de alcance" in response.json()['detail']
