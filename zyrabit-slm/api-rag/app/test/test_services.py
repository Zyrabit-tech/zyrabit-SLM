import pytest
import httpx
from unittest.mock import patch, MagicMock
import sys

# Mock chromadb globally to prevent pydantic v1 ConfigError in local Python 3.12+ testing
sys.modules['chromadb'] = MagicMock()
import chromadb

from app import services
MOCK_SLM_URL = "http://fake-SLM-server:11434"
MOCK_DB_URL = "http://fake-chroma-db:8000"

@patch.dict('os.environ', {'SLM_URL': MOCK_SLM_URL})
@patch('httpx.post')
def test_get_slm_router_decision_calls_SLM_and_parses_response(
        mock_httpx_post):
    query = "¿Qué opina Robert C. Martin sobre la architecture?"
    decision = services.get_slm_router_decision(query)
    assert decision == "search_rag_database"

@patch.dict('os.environ', {'SLM_URL': MOCK_SLM_URL, 'DB_URL': MOCK_DB_URL})
@patch('app.services.query_secure_slm')
@patch('app.services._create_embeddings')
@patch('chromadb.HttpClient')
def test_execute_rag_pipeline_retrieves_augments_and_generates(
        mock_chroma_client, mock_embeddings, mock_query_secure_slm):
    query = "¿Qué opina Robert C. Martin sobre la architecture?"
    mock_collection = MagicMock()
    mock_collection.query.return_value = {'documents': [
        ["El framework es un detalle que debe vivir en la capa externa."]]}
    mock_chroma_instance = mock_chroma_client.return_value
    mock_chroma_instance.get_or_create_collection.return_value = mock_collection
    mock_query_secure_slm.return_value = ("Robert C. Martin opina que el framework es un detalle.", 0.5)
    final_answer = services.execute_rag_pipeline(query)
    assert "Robert C. Martin opina que el framework es un detalle." in final_answer

@patch.dict('os.environ', {'SLM_URL': MOCK_SLM_URL})
def test_get_slm_router_decision_network_error():
    query = "¿Qué es Python?"
    decision = services.get_slm_router_decision(query)
    assert decision == "direct_SLM_answer"

@patch.dict('os.environ', {'SLM_URL': MOCK_SLM_URL, 'DB_URL': MOCK_DB_URL})
@patch('app.services._create_embeddings')
@patch('app.services._get_chroma_collection')
def test_execute_rag_pipeline_chroma_connection_error(mock_get_chroma, mock_embeddings):
    mock_get_chroma.side_effect = Exception("Connection to ChromaDB failed")
    query = "¿Qué opina Robert C. Martin sobre los frameworks?"
    final_answer = services.execute_rag_pipeline(query)
    assert "error" in final_answer.lower()

@patch.dict('os.environ', {'DB_URL': MOCK_DB_URL})
@patch('app.services._get_chroma_collection')
@patch('app.services._create_embeddings')
@patch('app.services.os.path.basename')
def test_process_and_ingest_file_success(
        mock_basename,
        mock_embeddings,
        mock_get_chroma):
    file_path = "/tmp/test.pdf"
    mock_basename.return_value = "test.pdf"
    
    with patch('langchain_community.document_loaders.PyMuPDFLoader') as mock_pdf_loader:
        mock_doc = MagicMock()
        mock_doc.page_content = "Este es el contenido de la página 1"
        mock_doc.metadata = {"page": 1, "source": file_path}
        mock_loader_instance = mock_pdf_loader.return_value
        mock_loader_instance.load.return_value = [mock_doc]
        
        result = services.process_and_ingest_file(file_path)
        assert result["status"] == "success"

@patch('langchain_community.document_loaders.PyMuPDFLoader')
def test_process_and_ingest_file_invalid_pdf(mock_pdf_loader):
    file_path = "/tmp/corrupted.pdf"
    mock_pdf_loader.side_effect = Exception("Invalid PDF")
    with pytest.raises(Exception):
        services.process_and_ingest_file(file_path)
