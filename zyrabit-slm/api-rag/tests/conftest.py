import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    """
    Returns a TestClient for the FastAPI app. 
    The app is imported inside the fixture to ensure it is 
    initialized AFTER infrastructure mocks are applied.
    """
    from app.main import app
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def mock_infrastructure():
    """
    Global fixture that prevents tests from connecting to real infrastructure.
    """
    mock_chroma = MagicMock()
    mock_chroma.heartbeat.return_value = True
    mock_chroma.similarity_search.return_value = []

    mock_inference = MagicMock()
    mock_inference.health.return_value = {"ok": True, "status": "CONNECTED"}
    mock_inference.provider_name = "mock-provider"
    mock_inference.generate.return_value = MagicMock(
        text="Mocked inference response.",
        latency_seconds=0.05,
        provider="mock",
        raw_payload={},
    )

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = []

    with patch(
        "app.infrastructure.persistence.chroma_adapter.ChromaAdapter",
        return_value=mock_chroma,
    ), patch(
        "app.infrastructure.inference.ollama_inference_adapter.OllamaInferenceAdapter",
        return_value=mock_inference,
    ), patch(
        "app.domain.services.retriever_service.HybridRetrieverService",
        return_value=mock_retriever,
    ), patch(
        "langchain_chroma.Chroma",
        return_value=MagicMock(),
    ), patch(
        "app.auto_ingest.run_auto_ingest",
        new=AsyncMock(return_value=None),
    ):
        from app.main import app
        # Ensure state is set before each test
        app.state.vector_store = mock_chroma
        app.state.inference_provider = mock_inference
        app.state.retriever_service = mock_retriever
        
        from app.domain.use_cases.chat_use_case import ChatUseCase
        from app.domain.use_cases.ingest_use_case import IngestUseCase
        from app.domain.services.gatekeeper import Gatekeeper
        from app.infrastructure.shared.cache import global_cache
        
        app.state.chat_use_case = ChatUseCase(
            inference_provider=mock_inference,
            retriever_service=mock_retriever,
            gatekeeper=Gatekeeper,
            cache=global_cache
        )
        app.state.ingest_use_case = IngestUseCase(vector_store=mock_chroma)

        yield {
            "vector_store": mock_chroma,
            "inference": mock_inference,
            "retriever": mock_retriever,
            "chat_use_case": app.state.chat_use_case
        }


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Ensure environment variables don't affect test behaviour."""
    monkeypatch.setenv("DOCS_DIR", "/tmp/zyrabit_test_docs")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("SLM_URL", "http://localhost:11434")
    monkeypatch.setenv("DB_URL", "http://localhost:8000")
    monkeypatch.setenv("MODEL_NAME", "qwen2.5:7b")
    monkeypatch.setenv("DB_PATH", "/tmp/test_sovereign.db")
    monkeypatch.setenv("TESTING", "true")


