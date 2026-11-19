"""Regression tests for the failure shown in the Prospeo screenshot.

These use two real documents already present in the local project. They prove
that selecting Prospeo cannot return CIO Review evidence.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.node.parsers import LocalDocumentParser
from app.node.service import NodeService
from app.node.sqlite_store import SQLiteNodeStore
from app.node.storage import LocalSourceStore
from tests.node.fakes import InMemoryVectorIndex


class CitingInference:
    def health(self): return True, "test"
    def answer(self, prompt):
        match = NodeService._EVIDENCE_CITE.search(prompt)
        if not match:
            return "Respuesta del modelo sin evidencia documental local.", {"provider": "contract-test"}
        evidence_id = match.group(1)
        return f"Respuesta basada únicamente en el documento seleccionado. [EVIDENCE:{evidence_id}]", {"provider": "contract-test"}


async def _ready(service: NodeService, job_id: str) -> None:
    for _ in range(200):
        job = service.job(job_id)
        if job["status"] == "ready": return
        assert job["status"] != "failed", job["error"]
        await asyncio.sleep(0.03)
    raise AssertionError("Indexing did not finish")


@pytest.mark.asyncio
async def test_selected_document_never_returns_other_document_sources(tmp_path: Path):
    root = Path(__file__).parents[3]
    cio = root / "api-rag/docs/zyrabit-cioreview-en.pdf"
    prospeo = root / "api-rag/docs/zyrabit-architecture-playbook.pdf"
    assert cio.exists() and prospeo.exists(), "Acceptance documents must remain available"
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")), LocalDocumentParser(), CitingInference(), vector_index=InMemoryVectorIndex())
    cio_import = await service.import_file(cio.name, str(cio))
    prospeo_import = await service.import_file(prospeo.name, str(prospeo))
    await _ready(service, cio_import["job_id"]); await _ready(service, prospeo_import["job_id"])

    result = await service.query("Arquitectura de Nodo Soberano Zyrabit", "scope-test", prospeo_import["document_id"])
    assert result["metadata"]["sources"], result
    assert {source["document_id"] for source in result["metadata"]["sources"]} == {prospeo_import["document_id"]}
    assert {source["filename"] for source in result["metadata"]["sources"]} == {prospeo.name}


@pytest.mark.asyncio
async def test_unready_selected_document_uses_model_without_falling_back_to_library(tmp_path: Path):
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")), LocalDocumentParser(), CitingInference(), vector_index=InMemoryVectorIndex())
    result = await service.query("anything", "scope-test", "missing-document")
    assert result["metadata"]["decision"] == "model-knowledge"
    assert result["metadata"]["sources"] == []


@pytest.mark.asyncio
async def test_document_owner_authorization_blocks_unauthorized_caller(tmp_path: Path):
    """Regression test for GHSA-2cwj-m6g5-8f69 (CWE-639).

    Ensure caller cannot query a document scoped to another owner_id.
    """
    store = SQLiteNodeStore(str(tmp_path / "node.db"))
    service = NodeService(store, LocalSourceStore(str(tmp_path / "sources")), LocalDocumentParser(), CitingInference(), vector_index=InMemoryVectorIndex())

    root = Path(__file__).parents[3]
    doc_file = root / "api-rag/docs/zyrabit-architecture-playbook.pdf"
    doc_import = await service.import_file(doc_file.name, str(doc_file))
    await _ready(service, doc_import["job_id"])
    doc_id = doc_import["document_id"]

    # Assign an owner to the source
    with store._connect() as conn:
        conn.execute("UPDATE node_sources SET owner_id = 'tenant-alice'")

    # Query with matching caller_id succeeds
    res_allowed = await service.query("Arquitectura", "s1", doc_id, caller_id="tenant-alice")
    assert res_allowed["metadata"]["sources"]

    # Query with mismatched caller_id is denied access to the document
    res_denied = await service.query("Arquitectura", "s2", doc_id, caller_id="tenant-bob")
    assert res_denied["metadata"]["sources"] == []
