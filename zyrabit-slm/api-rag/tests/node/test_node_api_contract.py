"""HTTP contract tests for the durable Node API using the approved PDF."""
from __future__ import annotations

import re
import time
from pathlib import Path

import pytest

from app.node.parsers import LocalDocumentParser
from app.node.service import NodeService
from app.node.sqlite_store import SQLiteNodeStore
from app.node.storage import LocalSourceStore


class CitingInference:
    def health(self): return True, "test"
    def answer(self, prompt):
        identifier = re.search(r"id=([0-9a-f-]{36})", prompt).group(1)
        return f"Air-Gapped operation is described in the supplied evidence. [EVIDENCE:{identifier}]", {"provider": "api-contract"}


@pytest.fixture
def node_api(client, tmp_path):
    from app.main import app
    app.state.node_service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")), LocalDocumentParser(), CitingInference())
    return client


def test_import_job_query_and_sources_over_http(node_api):
    pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    with pdf.open("rb") as handle:
        response = node_api.post("/v1/sources/import", files={"file": (pdf.name, handle, "application/pdf")})
    assert response.status_code == 202
    accepted = response.json()
    for _ in range(100):
        job = node_api.get(f"/v1/jobs/{accepted['job_id']}").json()
        if job["status"] in {"ready", "failed"}: break
        time.sleep(0.03)
    assert job["status"] == "ready", job
    answer = node_api.post("/v1/query", json={"text": "What operation is crucial for regulated environments?", "session_id": "api-test", "document_id": accepted["document_id"]})
    assert answer.status_code == 200
    payload = answer.json()
    assert payload["metadata"]["sources"]
    assert {item["document_id"] for item in payload["metadata"]["sources"]} == {accepted["document_id"]}
    assert payload["metadata"]["sources"][0]["locator"]["page"] == 2
