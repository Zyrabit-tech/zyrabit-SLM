import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_inference_provider():
    with patch("app.inference_factory.create_inference_provider") as mock:
        yield mock

@pytest.fixture
def mock_chroma_client():
    with patch("chromadb.HttpClient") as mock:
        yield mock

def test_health_integrity_all_online(mock_inference_provider, mock_chroma_client):
    """
    Verifies that /health returns 200 OK when both Ollama and ChromaDB are reachable.
    """
    # GIVEN
    mock_provider = MagicMock()
    mock_provider.health.return_value = {"ok": True}
    mock_inference_provider.return_value = mock_provider
    
    mock_db = MagicMock()
    mock_db.heartbeat.return_value = 12345
    mock_chroma_client.return_value = mock_db

    # WHEN
    response = client.get("/health")

    # THEN
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["slm"] == "online"
    assert data["db"] == "online"

def test_health_integrity_ollama_offline(mock_inference_provider, mock_chroma_client):
    """
    Verifies that /health returns 503 when Ollama is unreachable.
    """
    # GIVEN
    mock_provider = MagicMock()
    mock_provider.health.return_value = {"ok": False} # Or it could throw
    mock_inference_provider.return_value = mock_provider
    
    mock_db = MagicMock()
    mock_db.heartbeat.return_value = 12345
    mock_chroma_client.return_value = mock_db

    # WHEN
    response = client.get("/health")

    # THEN
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["slm"] == "offline"
    assert data["db"] == "online"

def test_health_integrity_chromadb_offline(mock_inference_provider, mock_chroma_client):
    """
    Verifies that /health returns 503 when ChromaDB is unreachable.
    """
    # GIVEN
    mock_provider = MagicMock()
    mock_provider.health.return_value = {"ok": True}
    mock_inference_provider.return_value = mock_provider
    
    mock_db = MagicMock()
    mock_db.heartbeat.side_effect = Exception("Connection Refused")
    mock_chroma_client.return_value = mock_db

    # WHEN
    response = client.get("/health")

    # THEN
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["slm"] == "online"
    assert data["db"] == "offline"
