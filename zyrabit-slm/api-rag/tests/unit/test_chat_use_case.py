import pytest
from unittest.mock import MagicMock
from app.domain.use_cases.chat_use_case import ChatUseCase
from app.domain.services.gatekeeper import Gatekeeper

@pytest.mark.asyncio
async def test_chat_use_case_direct_answer():
    # 1. Setup Mocks
    mock_inference = MagicMock()
    mock_vector_store = MagicMock()
    
    # Mock return object for inference
    mock_response = MagicMock()
    mock_response.text = "Mocked Zyrabit answer"
    mock_inference.generate.return_value = mock_response
    
    use_case = ChatUseCase(
        inference_provider=mock_inference,
        vector_store=mock_vector_store,
        gatekeeper=Gatekeeper
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
    mock_inference.generate.return_value = mock_response
    
    use_case = ChatUseCase(
        inference_provider=mock_inference,
        vector_store=mock_vector_store,
        gatekeeper=Gatekeeper
    )
    
    # Text with PII
    result = await use_case.execute(text="My email is test@example.com")
    
    # Verify that the text sent to inference was masked
    # The first argument of the first call to generate
    called_prompt = mock_inference.generate.call_args[0][0]
    assert "[EMAIL_MASKED]" in called_prompt
    assert "test@example.com" not in called_prompt
    assert result["metadata"]["pii_detected"] is True
