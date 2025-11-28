from ingest import check_ollama_model, load_documents, split_documents, populate_vector_db
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Importar las funciones del script de ingesta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

# --- PRUEBA 1: Verificar Modelo Ollama Disponible ---


@patch('ingest.OllamaEmbeddings')
def test_check_ollama_model_available(mock_embeddings):
    """
    Prueba que check_ollama_model retorne True cuando el modelo está disponible.
    """
    # GIVEN
    mock_embeddings_instance = mock_embeddings.return_value
    mock_embeddings_instance.embed_query.return_value = [0.1, 0.2, 0.3]

    # WHEN
    result = check_ollama_model("mxbai-embed-large")

    # THEN
    assert result is True
    mock_embeddings.assert_called_once_with(model="mxbai-embed-large")


@patch('ingest.OllamaEmbeddings')
def test_check_ollama_model_unavailable(mock_embeddings):
    """
    Prueba que check_ollama_model retorne False cuando el modelo no está disponible.
    """
    # GIVEN
    mock_embeddings_instance = mock_embeddings.return_value
    mock_embeddings_instance.embed_query.side_effect = Exception(
        "Model not found")

    # WHEN
    result = check_ollama_model("mxbai-embed-large")

    # THEN
    assert result is False

# --- PRUEBA 2: Cargar Documentos ---


@patch('os.path.exists')
@patch('os.listdir')
@patch('ingest.PyPDFLoader')
def test_load_documents_success(mock_pdf_loader, mock_listdir, mock_exists):
    """
    Prueba que load_documents cargue PDFs exitosamente.
    """
    # GIVEN
    mock_exists.return_value = True
    mock_listdir.return_value = [
        "document1.pdf",
        "document2.pdf",
        "readme.txt"]

    # Mock del loader
    mock_doc1 = MagicMock()
    mock_doc1.page_content = "Content 1"
    mock_doc2 = MagicMock()
    mock_doc2.page_content = "Content 2"

    mock_loader_instance = mock_pdf_loader.return_value
    mock_loader_instance.load.side_effect = [[mock_doc1], [mock_doc2]]

    # WHEN
    docs = load_documents("document_source")

    # THEN
    assert len(docs) == 2
    assert mock_pdf_loader.call_count == 2


@patch('os.path.exists')
def test_load_documents_no_directory(mock_exists):
    """
    Prueba que load_documents termine si el directorio no existe.
    """
    # GIVEN
    mock_exists.return_value = False

    # WHEN/THEN
    with pytest.raises(SystemExit):
        load_documents("non_existent_dir")


@patch('os.path.exists')
@patch('os.listdir')
def test_load_documents_no_pdfs(mock_listdir, mock_exists):
    """
    Prueba que load_documents termine si no hay archivos PDF.
    """
    # GIVEN
    mock_exists.return_value = True
    mock_listdir.return_value = ["readme.txt", "data.csv"]

    # WHEN/THEN
    with pytest.raises(SystemExit):
        load_documents("document_source")

# --- PRUEBA 3: Dividir Documentos ---


def test_split_documents_correct_chunks():
    """
    Prueba que split_documents divida los documentos en chunks correctamente.
    """
    # GIVEN
    mock_doc = MagicMock()
    # Crear contenido largo para que se divida en múltiples chunks
    mock_doc.page_content = "A" * 3000  # 3000 caracteres
    mock_doc.metadata = {"page": 1}

    docs = [mock_doc]

    # WHEN
    chunks = split_documents(docs)

    # THEN
    # Con CHUNK_SIZE=1000, deberíamos tener al menos 3 chunks
    assert len(chunks) >= 3
    # Verificar que cada chunk no exceda el tamaño máximo
    for chunk in chunks:
        # Con overlap podría ser un poco más
        assert len(chunk.page_content) <= 1200

# --- PRUEBA 4: Poblar Vector DB ---


@patch('chromadb.HttpClient')
@patch('ingest.OllamaEmbeddings')
def test_populate_vector_db_batching(mock_embeddings, mock_chroma_client):
    """
    Prueba que populate_vector_db ingeste chunks en batches correctamente.
    """
    # GIVEN
    mock_chunks = []
    for i in range(250):  # 250 chunks para probar batching
        mock_chunk = MagicMock()
        mock_chunk.page_content = f"Content {i}"
        mock_chunk.metadata = {"page": i}
        mock_chunks.append(mock_chunk)

    # Mock de embeddings
    mock_embeddings_instance = mock_embeddings.return_value
    # Retornar un embedding por cada chunk
    mock_embeddings_instance.embed_documents.return_value = [
        [0.1, 0.2] for _ in range(250)]

    # Mock de ChromaDB
    mock_collection = MagicMock()
    mock_collection.count.return_value = 250
    mock_chroma_instance = mock_chroma_client.return_value
    mock_chroma_instance.get_or_create_collection.return_value = mock_collection

    # WHEN
    populate_vector_db(mock_chunks, mock_embeddings_instance)

    # THEN
    # Con batch_size=100, deberíamos tener 3 llamadas a collection.add
    assert mock_collection.add.call_count == 3
    mock_collection.count.assert_called_once()


@patch('chromadb.HttpClient')
def test_populate_vector_db_connection_error(mock_chroma_client):
    """
    Prueba que populate_vector_db termine si no puede conectar a ChromaDB.
    """
    # GIVEN
    mock_chroma_client.side_effect = Exception("Connection refused")
    mock_chunks = [MagicMock()]
    mock_embeddings = MagicMock()

    # WHEN/THEN
    with pytest.raises(SystemExit):
        populate_vector_db(mock_chunks, mock_embeddings)
