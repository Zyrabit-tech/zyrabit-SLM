import pytest
from unittest.mock import MagicMock, patch
from app.domain.use_cases.chat_use_case import ChatUseCase


@pytest.fixture(autouse=True)
def mock_sovereign_state():
    """Prevent any real SQLite calls in unit tests."""
    with patch(
        "app.domain.use_cases.chat_use_case.SovereignStateManager"
    ) as mock_ssm:
        mock_ssm.get_user_profile.return_value = {}
        mock_ssm.get_history.return_value = []
        mock_ssm.store_message.return_value = None
        yield mock_ssm


@pytest.fixture
def mock_infra():
    """Provides mocked infrastructure ports."""
    return {
        "inference": MagicMock(),
        "vector_store": MagicMock(),
        "gatekeeper": MagicMock(),
        "cache": MagicMock()
    }

@pytest.mark.asyncio
async def test_chat_use_case_cache_hit(mock_infra):
    # Setup
    use_case = ChatUseCase(
        mock_infra["inference"],
        mock_infra["vector_store"],
        mock_infra["gatekeeper"],
        mock_infra["cache"],
        MagicMock()
    )
    
    # Simulate a cache hit
    mock_infra["cache"].get.return_value = {"response": "I am cached", "metadata": {"cached": True}}
    
    # Execute
    result = await use_case.execute("hello", client_msg_id="123")
    
    # Verify
    assert result["response"] == "I am cached"
    assert result["metadata"]["cached"] is True
    mock_infra["inference"].generate.assert_not_called()

@pytest.mark.asyncio
async def test_chat_use_case_pii_masking_integration(mock_infra):
    # Setup
    use_case = ChatUseCase(
        mock_infra["inference"],
        mock_infra["vector_store"],
        mock_infra["gatekeeper"],
        mock_infra["cache"],
        MagicMock()
    )
    
    mock_infra["cache"].get.return_value = None
    mock_infra["gatekeeper"].mask_pii.return_value = ("Hello [EMAIL]", {"email": ["admin@zyrabit.ai"]})
    mock_infra["gatekeeper"].get_routing_decision.return_value = "direct"
    
    # Mock inference result
    mock_res = MagicMock()
    mock_res.text = "Hello masked user"
    mock_res.latency_seconds = 0.1
    mock_res.raw_payload = {}
    mock_infra["inference"].generate.return_value = mock_res
    
    # Execute
    result = await use_case.execute("My email is admin@zyrabit.ai", client_msg_id="456")
    
    # Verify
    assert result["metadata"]["pii_detected"] is True
    # The prompt sent to inference should have been the masked one
    args, _ = mock_infra["inference"].generate.call_args
    assert "Hello [EMAIL]" in args[0].prompt
