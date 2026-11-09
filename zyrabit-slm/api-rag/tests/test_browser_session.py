"""The browser session keeps the service credential on the server."""

import time

from fastapi.testclient import TestClient

from app.core.security.api_key_store import ApiKeyStore
from app.core.security.auth import get_current_user
from app.main import app


def _client(monkeypatch):
    monkeypatch.setenv("ZYRABIT_API_KEY_WEB", "web-session-key")
    monkeypatch.setenv("ZYRABIT_COOKIE_SECURE", "false")
    monkeypatch.setenv("ZYRABIT_COOKIE_SAMESITE", "lax")
    ApiKeyStore.load()
    saved = app.dependency_overrides.pop(get_current_user, None)
    client = TestClient(app)
    return client, saved


def test_session_cookie_authenticates_without_exposing_the_key(monkeypatch):
    client, saved = _client(monkeypatch)
    try:
        opened = client.post("/v1/session", json={"token": "web-session-key"})
        assert opened.status_code == 200
        assert opened.json()["client"] == "web"
        assert "web-session-key" not in opened.text
        set_cookie = opened.headers.get("set-cookie", "")
        assert "zyrabit_session=" in set_cookie
        assert "HttpOnly" in set_cookie

        who = client.get("/v1/session")
        assert who.status_code == 200
        assert who.json()["client"] == "web"

        missing_csrf = client.delete("/v1/session")
        assert missing_csrf.status_code == 403

        csrf = client.cookies.get("zyrabit_csrf")
        closed = client.delete("/v1/session", headers={"X-CSRF-Token": csrf})
        assert closed.status_code == 200
        assert client.get("/v1/session").status_code == 401
    finally:
        if saved:
            app.dependency_overrides[get_current_user] = saved


def test_expired_session_is_rejected(monkeypatch):
    client, saved = _client(monkeypatch)
    try:
        opened = client.post("/v1/session", json={"token": "web-session-key"})
        assert opened.status_code == 200
        session_id = client.cookies.get("zyrabit_session")
        app.state.sessions._rows[session_id]["expires_at"] = time.time() - 1
        assert client.get("/v1/session").status_code == 401
    finally:
        if saved:
            app.dependency_overrides[get_current_user] = saved
