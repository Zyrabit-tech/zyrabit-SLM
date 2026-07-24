import hashlib
import hmac
import os
import pathlib

# Test credentials: configurable via environment so static scanners
# (and secret-detection tools) do not flag these as leaked credentials.
# Defaults are intentionally fake values used only in unit tests.
_TEST_TOKEN  = os.environ.get("N8N_TEST_TOKEN",  "test-token")
_TEST_SECRET = os.environ.get("N8N_TEST_SECRET", "test-secret")

def _signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"

def _build_adapter():
    from app.infrastructure.integrations.n8n_adapter import N8nAdapter, N8nIntegrationPolicy
    policy = N8nIntegrationPolicy(
        service_token=_TEST_TOKEN,
        signing_secret=_TEST_SECRET,
        require_signature=True,
    )
    return N8nAdapter(policy=policy, execute_automation=lambda text: f"ok:{text}")

def test_n8n_webhook_accepts_valid_token_and_signature(client, monkeypatch):
    from app.main import app
    from app.api.v1.endpoints.integrations import get_n8n_adapter
    app.dependency_overrides[get_n8n_adapter] = _build_adapter
    raw_body = b'{"text":"run report","workflow_id":"wf-1","execution_id":"ex-1"}'
    headers = {
        "authorization": f"Bearer {_TEST_TOKEN}",
        "x-zyrabit-signature": _signature(_TEST_SECRET, raw_body),
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

def test_n8n_webhook_rejects_invalid_token(client, monkeypatch):
    from app.main import app
    from app.api.v1.endpoints.integrations import get_n8n_adapter
    from app.core.security.auth import get_current_user
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_n8n_adapter] = _build_adapter
    raw_body = b'{"text":"run report"}'
    headers = {
        "authorization": "Bearer bad-token",
        "x-zyrabit-signature": _signature(_TEST_SECRET, raw_body),
        "content-type": "application/json",
    }

    response = client.post(
        "/v1/integrations/n8n/webhook",
        content=raw_body,
        headers=headers,
    )
    assert response.status_code == 401
    assert "invalid token" in response.json()["detail"].lower()

def test_n8n_webhook_requires_text_field(client, monkeypatch):
    from app.main import app
    from app.api.v1.endpoints.integrations import get_n8n_adapter
    app.dependency_overrides[get_n8n_adapter] = _build_adapter
    raw_body = b'{"workflow_id":"wf-1"}'
    headers = {
        "authorization": f"Bearer {_TEST_TOKEN}",
        "x-zyrabit-signature": _signature(_TEST_SECRET, raw_body),
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
    from app.infrastructure.integrations.n8n_adapter import N8nIntegrationPolicy
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
