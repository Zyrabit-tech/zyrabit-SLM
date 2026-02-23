import hashlib
import hmac

from fastapi.testclient import TestClient

from app.main import app
from app.adapters.n8n_adapter import N8nAdapter, N8nIntegrationPolicy


client = TestClient(app)


def _signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _build_adapter() -> N8nAdapter:
    policy = N8nIntegrationPolicy(
        service_token="test-token",
        signing_secret="test-secret",
        require_signature=True,
    )
    return N8nAdapter(policy=policy, execute_automation=lambda text: f"ok:{text}")


def test_n8n_webhook_accepts_valid_token_and_signature(monkeypatch):
    monkeypatch.setattr("app.main.n8n_adapter", _build_adapter())
    raw_body = b'{"text":"run report","workflow_id":"wf-1","execution_id":"ex-1"}'
    headers = {
        "authorization": "Bearer test-token",
        "x-zyrabit-signature": _signature("test-secret", raw_body),
        "content-type": "application/json",
    }

    response = client.post(
        "/v1/integrations/n8n/webhook",
        content=raw_body,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["provider"] == "n8n"
    assert data["response"] == "ok:run report"


def test_n8n_webhook_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr("app.main.n8n_adapter", _build_adapter())
    raw_body = b'{"text":"run report"}'
    headers = {
        "authorization": "Bearer bad-token",
        "x-zyrabit-signature": _signature("test-secret", raw_body),
        "content-type": "application/json",
    }

    response = client.post(
        "/v1/integrations/n8n/webhook",
        content=raw_body,
        headers=headers,
    )
    assert response.status_code == 401
    assert "invalid n8n bearer token" in response.json()["detail"].lower()


def test_n8n_webhook_requires_text_field(monkeypatch):
    monkeypatch.setattr("app.main.n8n_adapter", _build_adapter())
    raw_body = b'{"workflow_id":"wf-1"}'
    headers = {
        "authorization": "Bearer test-token",
        "x-zyrabit-signature": _signature("test-secret", raw_body),
        "content-type": "application/json",
    }

    response = client.post(
        "/v1/integrations/n8n/webhook",
        content=raw_body,
        headers=headers,
    )
    assert response.status_code == 400
    assert "text" in response.json()["detail"].lower()
