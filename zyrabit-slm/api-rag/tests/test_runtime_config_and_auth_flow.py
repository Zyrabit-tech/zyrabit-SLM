"""
Test runtime config endpoint and zero-config local auth.
Validates that /runtime-config.js supplies a valid token accepted by protected /v1 endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security.api_key_store import ApiKeyStore
from app.core.security.auth import get_current_user
from app.node.service import NodeService
from app.node.sqlite_store import SQLiteNodeStore
from app.node.storage import LocalSourceStore
from app.node.parsers import LocalDocumentParser
from tests.node.fakes import InMemoryVectorIndex

class DummyInference:
    def health(self): return True, "test"
    def answer(self, prompt): return "Answer", {"provider": "test"}

@pytest.fixture(autouse=True)
def configure_test_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("ZYRABIT_API_KEY_WEBUI", "test-webui-token-xyz")
    ApiKeyStore.load()
    app.state.node_service = NodeService(
        SQLiteNodeStore(str(tmp_path / "node.db")),
        LocalSourceStore(str(tmp_path / "sources")),
        LocalDocumentParser(),
        DummyInference(),
        vector_index=InMemoryVectorIndex()
    )
    # Remove global mock dependency_override to test real auth enforcement
    saved_override = app.dependency_overrides.pop(get_current_user, None)
    yield
    if saved_override:
        app.dependency_overrides[get_current_user] = saved_override

def test_runtime_config_endpoint_returns_javascript_with_token():
    client = TestClient(app)
    response = client.get("/runtime-config.js")
    assert response.status_code == 200
    assert "application/javascript" in response.headers.get("content-type", "")
    assert 'window.ZYRABIT_RUNTIME_CONFIG = { apiToken: "test-webui-token-xyz" };' in response.text

def test_token_from_runtime_config_authenticates_protected_endpoints():
    client = TestClient(app)
    token = "test-webui-token-xyz"

    # 1. Without token: must fail with 401
    unauthed = client.get("/v1/node/documents")
    assert unauthed.status_code == 401
    assert "Bearer token required" in unauthed.json()["detail"]

    # 2. With invalid token: must fail with 401
    bad_token = client.get("/v1/node/documents", headers={"Authorization": "Bearer wrong-token"})
    assert bad_token.status_code == 401

    # 3. With token from runtime config: must succeed (200)
    authed = client.get("/v1/node/documents", headers={"Authorization": f"Bearer {token}"})
    assert authed.status_code == 200
    assert "documents" in authed.json()
