import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def mock_infrastructure():
    """
    Global fixture to prevent tests from connecting to real infrastructure.
    It mocks the dependency factories in app.main.
    """
    with patch("app.main.get_vector_store_adapter") as mock_vdb, \
         patch("app.main.get_inference_adapter") as mock_inference:
        
        # Setup Mock Vector Store
        mock_vdb_instance = MagicMock()
        mock_vdb_instance.heartbeat.return_value = True
        mock_vdb.return_value = mock_vdb_instance
        
        # Setup Mock Inference
        mock_inf_instance = MagicMock()
        mock_inf_instance.health.return_value = {"ok": True, "status": "CONNECTED"}
        mock_inf_instance.provider_name = "mock-provider"
        mock_inference.return_value = mock_inf_instance
        
        # Patching the Use Case methods to be more resilient
        with patch("app.domain.use_cases.ChatUseCase.execute_rag") as mock_rag, \
             patch("app.domain.use_cases.ChatUseCase.execute_direct_chat") as mock_direct:
            
            mock_rag.return_value = ("Mocked RAG response", 1, 0.1, ["source.txt"])
            mock_direct.return_value = ("Mocked direct response", 0.05)
            
            yield {
                "vector_store": mock_vdb_instance,
                "inference": mock_inf_instance,
                "rag": mock_rag,
                "direct": mock_direct
            }

@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Ensure environment variables don't affect tests."""
    monkeypatch.setenv("DOCS_DIR", "/tmp/zyrabit_test_docs")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
