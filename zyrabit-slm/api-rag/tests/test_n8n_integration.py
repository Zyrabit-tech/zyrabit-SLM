import hashlib
import hmac
import pathlib

from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.integrations.n8n_adapter import N8nAdapter, N8nIntegrationPolicy


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
    from app.api.v1.endpoints.integrations import get_n8n_adapter
    app.dependency_overrides[get_n8n_adapter] = _build_adapter
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
    from app.api.v1.endpoints.integrations import get_n8n_adapter
    app.dependency_overrides[get_n8n_adapter] = _build_adapter
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
    from app.api.v1.endpoints.integrations import get_n8n_adapter
    app.dependency_overrides[get_n8n_adapter] = _build_adapter
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


def test_n8n_policy_reads_secrets_from_file(monkeypatch, tmp_path):
    token_path = tmp_path / "n8n_service_token"
    signing_path = tmp_path / "n8n_webhook_signing_secret"
    token_path.write_text("file-token", encoding="utf-8")
    signing_path.write_text("file-secret", encoding="utf-8")

    monkeypatch.delenv("N8N_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("N8N_WEBHOOK_SIGNING_SECRET", raising=False)
    monkeypatch.setenv("N8N_SERVICE_TOKEN_FILE", str(pathlib.Path(token_path)))
    monkeypatch.setenv(
        "N8N_WEBHOOK_SIGNING_SECRET_FILE",
        str(pathlib.Path(signing_path)),
    )
    monkeypatch.setenv("N8N_REQUIRE_SIGNATURE", "true")

    policy = N8nIntegrationPolicy.from_env()
    assert policy.service_token == "file-token"
    assert policy.signing_secret == "file-secret"
