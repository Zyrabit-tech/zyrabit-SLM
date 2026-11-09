"""A signed-in client is not automatically allowed to delete documents."""

import pytest
from fastapi.testclient import TestClient

from app.core.security.api_key_store import ApiKeyStore
from app.core.security.auth import get_current_user
from app.main import app
from app.node.parsers import LocalDocumentParser
from app.node.service import NodeService
from app.node.sqlite_store import SQLiteNodeStore
from app.node.storage import LocalSourceStore
from tests.node.fakes import InMemoryVectorIndex


class DummyInference:
    def health(self):
        return True, "test"

    def answer(self, prompt):
        return "Answer", {"provider": "test"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("ZYRABIT_API_KEY_WEB", "web-key")
    monkeypatch.setenv("ZYRABIT_API_KEY_ADMIN", "admin-key")
    monkeypatch.setenv("ZYRABIT_ADMIN_CLIENTS", "admin")
    ApiKeyStore.load()
    app.state.node_service = NodeService(
        SQLiteNodeStore(str(tmp_path / "node.db")),
        LocalSourceStore(str(tmp_path / "sources")),
        LocalDocumentParser(),
        DummyInference(),
        vector_index=InMemoryVectorIndex(),
    )
    saved = app.dependency_overrides.pop(get_current_user, None)
    test_client = TestClient(app)
    yield test_client
    if saved:
        app.dependency_overrides[get_current_user] = saved


def test_web_identity_cannot_delete_and_leaves_documents_unchanged(client, tmp_path):
    source = tmp_path / "note.txt"
    source.write_text("sovereign note", encoding="utf-8")
    uploaded = client.post(
        "/v1/sources/import",
        headers={"Authorization": "Bearer web-key"},
        files={"file": ("note.txt", source.read_bytes(), "text/plain")},
    )
    assert uploaded.status_code == 202
    document_id = uploaded.json()["document_id"]

    denied = client.delete(
        f"/v1/documents/{document_id}",
        headers={"Authorization": "Bearer web-key"},
    )
    assert denied.status_code == 403
    assert client.get(
        f"/v1/documents/{document_id}",
        headers={"Authorization": "Bearer web-key"},
    ).status_code == 200


def test_admin_identity_can_delete(client):
    source_bytes = b"admin-owned note"
    uploaded = client.post(
        "/v1/sources/import",
        headers={"Authorization": "Bearer admin-key"},
        files={"file": ("note.txt", source_bytes, "text/plain")},
    )
    assert uploaded.status_code == 202
    document_id = uploaded.json()["document_id"]

    deleted = client.delete(
        f"/v1/documents/{document_id}",
        headers={"Authorization": "Bearer admin-key"},
    )
    assert deleted.status_code == 204
    assert client.get(
        f"/v1/documents/{document_id}",
        headers={"Authorization": "Bearer admin-key"},
    ).status_code == 404
