import os
import pytest
from app.core.security.api_key_store import ApiKeyStore
from app.core.security.auth import get_current_user
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

def test_api_key_store_load_and_validate(monkeypatch):
    monkeypatch.setenv("ZYRABIT_API_KEY_WEBUI", "web-secret-key-123")
    monkeypatch.setenv("ZYRABIT_API_KEY_N8N_CLIENT", "n8n-secret-key-456")
    monkeypatch.setenv("N8N_SERVICE_TOKEN", "legacy-token-789")

    # Reload store
    ApiKeyStore.load()

    # Validate correct keys
    assert ApiKeyStore.validate("web-secret-key-123") == "webui"
    assert ApiKeyStore.validate("n8n-secret-key-456") == "n8n_client"
    assert ApiKeyStore.validate("legacy-token-789") == "legacy_n8n"

    # Validate incorrect key
    assert ApiKeyStore.validate("wrong-key") is None

@pytest.mark.asyncio
async def test_get_current_user_valid(monkeypatch):
    monkeypatch.setenv("ZYRABIT_API_KEY_WEBUI", "web-secret-key-123")
    ApiKeyStore.load()

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="web-secret-key-123")
    user = await get_current_user(creds)
    assert user.name == "Admin"
    assert user.client == "webui"

@pytest.mark.asyncio
async def test_get_current_user_invalid(monkeypatch):
    monkeypatch.setenv("ZYRABIT_API_KEY_WEBUI", "web-secret-key-123")
    ApiKeyStore.load()

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-key")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 401
