import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture(autouse=True)
def mock_infrastructure():
    """
    Global fixture that prevents tests from connecting to real infrastructure.

    V5.0 architecture: ChatUseCase has a single execute() method. Infrastructure
    adapters are initialized in the lifespan and stored on app.state. We patch
    at the class/constructor level to return mock instances without a real
    Ollama or ChromaDB endpoint.
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

    mock_execute_result = {
        "response": "Mocked response",
        "metadata": {"decision": "rag", "latency_ms": 50.0, "sources": [], "pii_detected": False, "cached": False},
    }

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
    ), patch(
        "app.domain.use_cases.chat_use_case.ChatUseCase.execute",
        new=AsyncMock(return_value=mock_execute_result),
    ) as mock_execute:
        yield {
            "vector_store": mock_chroma,
            "inference": mock_inference,
            "retriever": mock_retriever,
            "execute": mock_execute,
        }


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Ensure environment variables don't affect test behaviour."""
    monkeypatch.setenv("DOCS_DIR", "/tmp/zyrabit_test_docs")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("SLM_URL", "http://localhost:11434")
    monkeypatch.setenv("DB_URL", "http://localhost:8000")
    monkeypatch.setenv("MODEL_NAME", "qwen2.5:7b")
