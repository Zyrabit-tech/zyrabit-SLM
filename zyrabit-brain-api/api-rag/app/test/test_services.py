import pytest
import httpx
from unittest.mock import patch, MagicMock
from app import services
import chromadb

# Variable de entorno simulada para la URL de Ollama
MOCK_LLM_URL = "http://fake-llm-server:11434"
MOCK_DB_URL = "http://fake-chroma-db:8000"

@patch.dict('os.environ', {'LLM_URL': MOCK_LLM_URL})
@patch('httpx.post')
def test_get_llm_router_decision_calls_llm_and_parses_response(mock_httpx_post):
    """
    Prueba que la función get_llm_router_decision:
    1. Llame a httpx.post con la URL y el meta-prompt correctos.
    2. Parseé la respuesta JSON del LLM.
    3. Devuelva el string de la decisión (ej. "search_rag_database").
    """
    # 1. GIVEN (Dado...)
    # Simulamos que Ollama responde correctamente
    mock_api_response = MagicMock()
    mock_api_response.status_code = 200
    # Esta es la estructura de respuesta de Ollama
    mock_api_response.json.return_value = {
        "model": "mistral:latest",
        "created_at": "2025-11-08T20:45:00.000Z",
        "response": "search_rag_database", # <-- ¡El valor que queremos!
        "done": True
    }
    mock_httpx_post.return_value = mock_api_response
    
    query = "¿Qué opina Robert C. Martin sobre los frameworks?"

    # 2. WHEN (Cuando...)
    # Llamamos a nuestra función REAL (que aún es un stub)
    decision = services.get_llm_router_decision(query)

    # 3. THEN (Entonces...)
    # Verificamos que se haya hecho la llamada HTTP a la URL correcta
    mock_httpx_post.assert_called_once()
    called_url = mock_httpx_post.call_args[0][0] # El primer argumento de post()
    assert called_url == f"{MOCK_LLM_URL}/api/generate"

    # Verificamos que la función parseó el JSON y devolvió el string limpio
    assert decision == "search_rag_database"

@patch.dict('os.environ', {'LLM_URL': MOCK_LLM_URL})
@patch('httpx.post')
def test_call_direct_llm_sends_clean_query_and_returns_response(mock_httpx_post):
    """
    Prueba que la función call_direct_llm (la ruta "fácil"):
    1. Llame a httpx.post con la URL y el payload correctos.
    2. El prompt enviado sea EXACTAMENTE la query del usuario.
    3. Devuelva la respuesta limpia del LLM.
    """
    # 1. GIVEN (Dado...)
    # Simulamos que Ollama responde a una pregunta general
    mock_api_response = MagicMock()
    mock_api_response.status_code = 200
    mock_api_response.json.return_value = {
        "response": "Python es un lenguaje de programación interpretado...",
        "done": True
    }
    mock_httpx_post.return_value = mock_api_response
    
    query = "¿Qué es Python?"

    # 2. WHEN (Cuando...)
    # Llamamos a nuestra función STUB
    response_text = services.call_direct_llm(query)

    # 3. THEN (Entonces...)
    # Verificamos que se hizo la llamada HTTP
    mock_httpx_post.assert_called_once()
    
    # Verificamos que el PAYLOAD enviado es el correcto
    call_payload = mock_httpx_post.call_args[1]['json'] # El kwarg 'json'
    assert call_payload['model'] == "mistral" # O el modelo que definamos
    assert call_payload['prompt'] == query # ¡Crítico! El prompt es la query directa
    assert call_payload['stream'] == False

    # Verificamos que la función devolvió el string limpio
    assert response_text == "Python es un lenguaje de programación interpretado..."

@patch.dict('os.environ', {'LLM_URL': MOCK_LLM_URL, 'DB_URL': MOCK_DB_URL})
@patch('chromadb.HttpClient') # Mockea la llamada de BÚSQUEDA (Chroma)
@patch('httpx.post') # Mockea la llamada de GENERACIÓN (Ollama)
def test_execute_rag_pipeline_retrieves_augments_and_generates(mock_httpx_post, mock_chroma_client):
    """
    Prueba que la función RAG completa:
    1. Inicialice el cliente de Chroma con la DB_URL.
    2. Llame al método 'query' de Chroma con la pregunta del usuario.
    3. Construya un "megaprompt" que incluya el contexto de Chroma.
    4. Llame a httpx.post (Ollama) con ese megaprompt.
    5. Devuelva la respuesta final de Ollama.
    """
    # 1. GIVEN (Dado...)
    query = "¿Qué opina Robert C. Martin sobre los frameworks?"
    
    # -- Mock de Chroma (Búsqueda) --
    mock_collection = MagicMock()
    # Simulamos que Chroma devuelve 1 chunk de contexto relevante
    mock_collection.query.return_value = {
        'documents': [["El framework es un detalle que debe vivir en la capa externa."]]
    }
    # Mockeamos el cliente para que devuelva nuestra colección mockeada
    mock_chroma_instance = mock_chroma_client.return_value
    mock_chroma_instance.get_or_create_collection.return_value = mock_collection

    # -- Mock de Ollama (Generación) --
    mock_llm_response = MagicMock()
    mock_llm_response.status_code = 200
    mock_llm_response.json.return_value = {
        "response": "Robert C. Martin opina que el framework es un detalle.",
        "done": True
    }
    mock_httpx_post.return_value = mock_llm_response

    # 2. WHEN (Cuando...)
    # Llamamos a nuestra función STUB
    final_answer = services.execute_rag_pipeline(query)

    # 3. THEN (Entonces...)
    # -- Verificamos la BÚSQUEDA --
    # ¿Se inicializó el cliente de Chroma con la URL correcta?
    mock_chroma_client.assert_called_with(host='fake-chroma-db', port=8000)
    # ¿Se buscó en la colección?
    mock_collection.query.assert_called_with(query_texts=[query], n_results=5) # Asumimos n_results=5

    # -- Verificamos la GENERACIÓN --
    # ¿Se llamó a Ollama?
    mock_httpx_post.assert_called_once()
    
    # ¿El prompt enviado a Ollama contenía el CONTEXTO y la PREGUNTA?
    call_payload = mock_httpx_post.call_args[1]['json']
    augmented_prompt = call_payload['prompt']
    
    assert "El framework es un detalle" in augmented_prompt # El contexto
    assert "¿Qué opina Robert C. Martin" in augmented_prompt # La pregunta

    # -- Verificamos la RESPUESTA FINAL --
    assert final_answer == "Robert C. Martin opina que el framework es un detalle."

# --- PRUEBAS DE MANEJO DE ERRORES ---

@patch.dict('os.environ', {'LLM_URL': MOCK_LLM_URL})
@patch('httpx.post')
def test_get_llm_router_decision_network_error(mock_httpx_post):
    """
    Prueba que get_llm_router_decision retorne un fallback seguro cuando hay error de red.
    """
    # GIVEN
    mock_httpx_post.side_effect = httpx.RequestError("Connection refused")
    query = "¿Qué es Python?"
    
    # WHEN
    decision = services.get_llm_router_decision(query)
    
    # THEN
    # Debe retornar el fallback seguro
    assert decision == "direct_llm_answer"

@patch.dict('os.environ', {'LLM_URL': MOCK_LLM_URL})
@patch('httpx.post')
def test_get_llm_router_decision_invalid_response(mock_httpx_post):
    """
    Prueba que maneje respuestas inválidas del LLM (decisión no reconocida).
    """
    # GIVEN
    mock_api_response = MagicMock()
    mock_api_response.status_code = 200
    mock_api_response.json.return_value = {
        "response": "invalid_tool_name",  # Decisión no válida
        "done": True
    }
    mock_httpx_post.return_value = mock_api_response
    
    query = "¿Qué es Python?"
    
    # WHEN
    decision = services.get_llm_router_decision(query)
    
    # THEN
    # Debe retornar el fallback seguro
    assert decision == "direct_llm_answer"

@patch.dict('os.environ', {'LLM_URL': MOCK_LLM_URL})
@patch('httpx.post')
def test_call_direct_llm_timeout(mock_httpx_post):
    """
    Prueba que call_direct_llm maneje timeouts correctamente.
    """
    # GIVEN
    mock_httpx_post.side_effect = httpx.TimeoutException("Request timed out")
    query = "¿Qué es Python?"
    
    # WHEN
    response_text = services.call_direct_llm(query)
    
    # THEN
    # Debe retornar un mensaje de error amigable
    assert "no pude contactar" in response_text.lower()

@patch.dict('os.environ', {'LLM_URL': MOCK_LLM_URL, 'DB_URL': MOCK_DB_URL})
@patch('chromadb.HttpClient')
def test_execute_rag_pipeline_chroma_connection_error(mock_chroma_client):
    """
    Prueba que execute_rag_pipeline maneje errores de conexión a ChromaDB.
    """
    # GIVEN
    mock_chroma_client.side_effect = Exception("Connection to ChromaDB failed")
    query = "¿Qué opina Robert C. Martin sobre los frameworks?"
    
    # WHEN
    final_answer = services.execute_rag_pipeline(query)
    
    # THEN
    # Debe retornar un mensaje de error amigable
    assert "error" in final_answer.lower()
    assert "base de datos" in final_answer.lower()

@patch.dict('os.environ', {'LLM_URL': MOCK_LLM_URL, 'DB_URL': MOCK_DB_URL})
@patch('chromadb.HttpClient')
@patch('httpx.post')
def test_execute_rag_pipeline_empty_results(mock_httpx_post, mock_chroma_client):
    """
    Prueba que execute_rag_pipeline maneje el caso cuando ChromaDB no retorna documentos.
    """
    # GIVEN
    query = "¿Qué es clean code?"
    
    # Mock de Chroma que retorna resultados vacíos
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        'documents': [[]]  # Sin documentos
    }
    mock_chroma_instance = mock_chroma_client.return_value
    mock_chroma_instance.get_or_create_collection.return_value = mock_collection
    
    # Mock de Ollama
    mock_llm_response = MagicMock()
    mock_llm_response.status_code = 200
    mock_llm_response.json.return_value = {
        "response": "No encontré información sobre eso en la base de conocimiento.",
        "done": True
    }
    mock_httpx_post.return_value = mock_llm_response
    
    # WHEN
    final_answer = services.execute_rag_pipeline(query)
    
    # THEN
    # Debe seguir funcionando, pero con contexto vacío
    assert isinstance(final_answer, str)
    mock_collection.query.assert_called_once()

@patch.dict('os.environ', {'DB_URL': MOCK_DB_URL})
@patch('chromadb.HttpClient')
@patch('langchain_ollama.OllamaEmbeddings')
@patch('langchain_community.document_loaders.PyPDFLoader')
def test_process_and_ingest_file_success(mock_pdf_loader, mock_embeddings, mock_chroma_client):
    """
    Prueba que process_and_ingest_file procese e ingeste un PDF correctamente.
    """
    # GIVEN
    file_path = "/tmp/test.pdf"
    
    # Mock del loader de PDF
    mock_doc = MagicMock()
    mock_doc.page_content = "Este es el contenido de la página 1"
    mock_doc.metadata = {"page": 1, "source": file_path}
    
    mock_loader_instance = mock_pdf_loader.return_value
    mock_loader_instance.load.return_value = [mock_doc]
    
    # Mock de embeddings
    mock_embeddings_instance = mock_embeddings.return_value
    mock_embeddings_instance.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    
    # Mock de ChromaDB
    mock_collection = MagicMock()
    mock_chroma_instance = mock_chroma_client.return_value
    mock_chroma_instance.get_or_create_collection.return_value = mock_collection
    
    # WHEN
    result = services.process_and_ingest_file(file_path)
    
    # THEN
    assert result["status"] == "success"
    assert result["chunks_processed"] > 0
    mock_pdf_loader.assert_called_once_with(file_path)
    mock_collection.add.assert_called()

@patch('langchain_community.document_loaders.PyPDFLoader')
def test_process_and_ingest_file_invalid_pdf(mock_pdf_loader):
    """
    Prueba que process_and_ingest_file maneje PDFs corruptos o inválidos.
    """
    # GIVEN
    file_path = "/tmp/corrupted.pdf"
    mock_pdf_loader.side_effect = Exception("Invalid PDF format")
    
    # WHEN/THEN
    with pytest.raises(Exception) as exc_info:
        services.process_and_ingest_file(file_path)
    
    assert "Invalid PDF" in str(exc_info.value)
