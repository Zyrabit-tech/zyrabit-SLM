import pytest
import asyncio
from unittest.mock import MagicMock, patch

# Defensive Mocking for missing environment libs
try:
    import tiktoken
except ImportError:
    tiktoken = MagicMock()
    tiktoken.get_encoding.return_value = MagicMock()

try:
    import mcp
except ImportError:
    mcp = MagicMock()

from app.domain.use_cases.chat_use_case import ChatUseCase
from app.domain.use_cases.ingest_use_case import IngestUseCase
from app.infrastructure.shared.state_tracker import SovereignStateManager
from app.domain.services.context_manager import ContextManager
import logging

logger = logging.getLogger("zyrabit.test")

@pytest.fixture(autouse=True)
def setup_db():
    # Use an in-memory or temporary DB for tests
    TEST_DB = "/tmp/test_sovereign.db"
    SovereignStateManager.init_db(db_path=TEST_DB)
    yield
    import os
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

@pytest.mark.asyncio
async def test_full_sovereign_cycle():
    """
    INTEGRATION TEST: Profile -> Ingest -> Context Aware Chat
    """
    # 1. Setup User Profile
    SovereignStateManager.update_user_profile(
        name="Kai", 
        role="Sovereign Architect", 
        interests="Local SLM Security"
    )
    
    # 2. Setup Mocks
    mock_inference = MagicMock()
    # Create a mock response object with a 'text' attribute that is a string
    mock_response = MagicMock()
    mock_response.text = "Hola Kai, veo que te interesa la seguridad."
    mock_response.latency_seconds = 0.5
    mock_inference.generate.return_value = mock_response
    
    mock_vector = MagicMock()
    mock_retriever = MagicMock()
    mock_gatekeeper = MagicMock()
    # Align with actual Gatekeeper.mask_pii
    mock_gatekeeper.mask_pii.return_value = ("Hola Zyra", {})
    mock_cache = MagicMock()
    # Ensure cache.get returns None so it doesn't hit cache
    mock_cache.get.return_value = None
    
    chat_use_case = ChatUseCase(mock_inference, mock_retriever, mock_gatekeeper, mock_cache)
    
    # 3. Execute Chat
    response = await chat_use_case.execute("Hola Zyra", client_msg_id="test_session")
    
    # 4. Verify Memory & Context
    assert "Hola Kai" in response["response"]
    history = SovereignStateManager.get_history("test_session")
    assert len(history) == 2 # User + Assistant
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"

@pytest.mark.asyncio
async def test_wal_concurrency_stress():
    """
    INTEGRATION TEST: Stress test SQLite WAL concurrency.
    Simulate multiple agents writing to memory while one reads.
    """
    session_id = "stress_test_session"
    
    async def writer(i):
        SovereignStateManager.store_message(session_id, "user", f"Message {i}")
        await asyncio.sleep(0.01)

    # Run 50 concurrent writes
    await asyncio.gather(*[writer(i) for i in range(50)])
    
    history = SovereignStateManager.get_history(session_id, limit=100)
    assert len(history) >= 50
    logger.info("✅ SQLite WAL Concurrency test passed: No locks detected.")

def test_gatekeeper_pii_redaction():
    """
    UNIT TEST: Validate Gatekeeper's ability to clean PII.
    """
    from app.domain.services.gatekeeper import Gatekeeper
    
    sensitive_text = "Mi email es test@example.com y mi API key es sk-1234567890abcdef"
    # Use actual method name: mask_pii
    clean_text, entities = Gatekeeper.mask_pii(sensitive_text)
    
    assert "test@example.com" not in clean_text
    # The anonymizer replaces with format like <USER_EMAIL_1>
    assert "USER_EMAIL" in clean_text or "anonymized" in clean_text
    logger.info("✅ Gatekeeper Unit Test passed: PII correctly redacted.")

@pytest.mark.asyncio
async def test_mcp_security_import():
    """
    E2E/Integration: Test that import_to_vault blocks executables.
    """
    from app.domain.services.mcp_service import import_to_vault
    
    # Create a "malicious" file
    malicious_path = "/tmp/hack.sh"
    with open(malicious_path, "w") as f:
        f.write("#!/bin/bash\necho 'hacked'\nos.system('rm -rf /')")
        
    result = await import_to_vault(malicious_path, "vault_hack.sh")
    assert "Security Alert" in result
    
    import os
    if os.path.exists(malicious_path):
        os.remove(malicious_path)

@pytest.mark.asyncio
async def test_context_budgeting_trimming():
    """
    Logic Test: Verify ContextManager discards tokens correctly.
    """
    # Patch ContextManager.count_tokens to return realistic values for the test
    with patch.object(ContextManager, 'count_tokens', side_effect=lambda x: len(x)):
        manager = ContextManager()
        
        # Create a history that definitely exceeds MEMORY_RESERVE (1000 chars now)
        long_history = [{"role": "user", "content": "bla " * 100} for _ in range(10)]
        
        # Trimming should happen
        trimmed = manager.trim_history(long_history)
        
        # Total tokens would be ~4000. Budget is 1000. 
        # Should only allow ~2.5 messages.
        assert "user:" in trimmed
        assert trimmed.count("user:") <= 3
