import pytest
from unittest.mock import MagicMock
from app.domain.use_cases.chat_use_case import ChatUseCase

@pytest.mark.asyncio
async def test_chat_use_case_direct_answer():
    # 1. Setup Mocks
    mock_inference = MagicMock()
    mock_vector_store = MagicMock()
    
    # Mock return object for inference
    mock_response = MagicMock()
    mock_response.text = "Mocked Zyrabit answer"
    mock_response.latency_seconds = 0.1
    mock_inference.generate.return_value = mock_response
    
    mock_gatekeeper = MagicMock()
    mock_gatekeeper.mask_pii.return_value = ("What is Zyrabit SLM?", {})
    mock_gatekeeper.get_routing_decision.return_value = "direct"
    
    use_case = ChatUseCase(
        mock_inference,
        mock_vector_store,
        mock_gatekeeper,
        MagicMock()
    )
    
    # 2. Execute
    result = await use_case.execute(text="What is Zyrabit SLM?")
    
    # 3. Assertions
    assert "Mocked Zyrabit answer" in result["response"]
    assert result["metadata"]["decision"] == "direct"
    mock_inference.generate.assert_called_once()
    mock_vector_store.similarity_search.assert_not_called()

@pytest.mark.asyncio
async def test_chat_use_case_pii_masking():
    mock_inference = MagicMock()
    mock_vector_store = MagicMock()
    
    mock_response = MagicMock()
    mock_response.text = "Answer sent to masked email"
    mock_response.latency_seconds = 0.1
    mock_inference.generate.return_value = mock_response
    
    mock_gatekeeper = MagicMock()
    mock_gatekeeper.mask_pii.return_value = ("My email is [EMAIL_MASKED]", {"email": ["test@example.com"]})
    mock_gatekeeper.get_routing_decision.return_value = "direct"

    use_case = ChatUseCase(
        mock_inference,
        mock_vector_store,
        mock_gatekeeper,
        MagicMock()
    )
    
    # Text with PII
    result = await use_case.execute(text="My email is test@example.com")
    
    # Verify that the text sent to inference was masked
    # The first argument of the first call to generate is an InferenceRequest
    called_request = mock_inference.generate.call_args[0][0]
    assert "[EMAIL_MASKED]" in called_request.prompt
    assert "test@example.com" not in called_request.prompt
    assert result["metadata"]["pii_detected"] is True
