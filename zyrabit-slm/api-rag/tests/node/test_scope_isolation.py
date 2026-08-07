"""Regression tests for the failure shown in the Prospeo screenshot.

These use two real documents already present in the local project. They prove
that selecting Prospeo cannot return CIO Review evidence.
"""
from __future__ import annotations

import asyncio
import re
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
        evidence_id = re.search(r"id=([0-9a-f-]{36})", prompt).group(1)
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
    prospeo = root / "document_source/- Playbook plataforma Prospeo.docx.pdf"
    assert cio.exists() and prospeo.exists(), "Acceptance documents must remain available"
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")), LocalDocumentParser(), CitingInference(), vector_index=InMemoryVectorIndex())
    cio_import = await service.import_file(cio.name, str(cio))
    prospeo_import = await service.import_file(prospeo.name, str(prospeo))
    await _ready(service, cio_import["job_id"]); await _ready(service, prospeo_import["job_id"])

    result = await service.query("Dame el playbook de la plataforma", "scope-test", prospeo_import["document_id"])
    assert result["metadata"]["sources"], result
    assert {source["document_id"] for source in result["metadata"]["sources"]} == {prospeo_import["document_id"]}
    assert {source["filename"] for source in result["metadata"]["sources"]} == {prospeo.name}


@pytest.mark.asyncio
async def test_unready_selected_document_fails_without_falling_back_to_library(tmp_path: Path):
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")), LocalDocumentParser(), CitingInference(), vector_index=InMemoryVectorIndex())
    result = await service.query("anything", "scope-test", "missing-document")
    assert result["metadata"]["decision"] == "selected-document-unavailable"
    assert result["metadata"]["sources"] == []
