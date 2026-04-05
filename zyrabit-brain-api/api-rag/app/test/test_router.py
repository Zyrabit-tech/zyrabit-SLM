import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Now we can safely import the app
from app.main import app

client = TestClient(app)

# --- TEST 1: The Router knows when to use RAG ---


@patch('app.services.execute_rag_pipeline_with_metadata')
@patch('app.services.get_slm_router_decision')
def test_router_sends_tech_queries_to_RAG(
        mock_router_decision, mock_rag_pipeline):
    """
    Test that a question about Robert C. Martin is routed to 'search_rag_database'.
    """
    # 1. GIVEN
    mock_router_decision.return_value = "search_rag_database"
    mock_rag_pipeline.return_value = ("[Respuesta RAG para: ¿Qué opina Robert C. Martin sobre los frameworks?]", 1)

    query = {"text": "¿Qué opina Robert C. Martin sobre los frameworks?"}

    # 2. WHEN
    response = client.post("/v1/chat", json=query)

    # 3. THEN
    mock_router_decision.assert_called_once_with(query['text'])
    mock_rag_pipeline.assert_called_once_with(query['text'])

    assert response.status_code == 200
    assert "Respuesta RAG para" in response.json()['response']

# --- TEST 2: The Router knows when NOT to use RAG (General Knowledge) ---


@patch('app.services.call_direct_slm')
@patch('app.services.execute_rag_pipeline_with_metadata')
@patch('app.services.get_slm_router_decision')
def test_router_sends_general_queries_to_DIRECT_SLM(
        mock_router_decision, mock_rag_pipeline, mock_direct_slm):
    """
    Test that a general question is routed to 'direct_SLM_answer'.
    """
    # 1. GIVEN
    mock_router_decision.return_value = "direct_SLM_answer"
    mock_direct_slm.return_value = "[Respuesta SLM Directa para: ¿Cómo estará el clima mañana?]"

    query = {"text": "¿Cómo estará el clima mañana?"}

    # 2. WHEN
    response = client.post("/v1/chat", json=query)

    # 3. THEN
    mock_router_decision.assert_called_once_with(query['text'])
    mock_rag_pipeline.assert_not_called()
    mock_direct_slm.assert_called_once_with(query['text'])

    assert response.status_code == 200
    assert "Respuesta SLM Directa para" in response.json()['response']

# --- TEST 3: The Router knows when to REJECT (Guardrail) ---


@patch('app.services.execute_rag_pipeline_with_metadata')
@patch('app.services.get_slm_router_decision')
def test_router_REJECTS_out_of_scope_queries(
        mock_router_decision, mock_rag_pipeline):
    """
    Test that the router rejects out-of-scope queries.
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
