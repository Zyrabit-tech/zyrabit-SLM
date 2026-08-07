"""Integration checks for the real, authorized Zyrabit CIO review document."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.node.parsers import LocalDocumentParser
from app.node.service import NodeService
from app.node.sqlite_store import SQLiteNodeStore
from app.node.storage import LocalSourceStore


class OfflineInference:
    """The import test deliberately does not require a running model."""
    def health(self): return True, "test"
    def answer(self, prompt):
        import re
        evidence_id = re.search(r"id=([0-9a-f-]{36})", prompt).group(1)
        return f"Air-Gapped operation is described as crucial for regulated environments. [EVIDENCE:{evidence_id}]", {"provider": "offline-test"}


@pytest.mark.asyncio
async def test_real_cio_review_pdf_is_durable_and_searchable(tmp_path: Path):
    source_pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    assert source_pdf.exists(), "The authorized acceptance PDF must be present"
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")),
                          LocalDocumentParser(), OfflineInference())
    accepted = await service.import_file(source_pdf.name, str(source_pdf))
    assert accepted["status"] == "queued"
    for _ in range(100):
        job = service.job(accepted["job_id"])
        if job["status"] in {"ready", "failed"}: break
        await asyncio.sleep(0.05)
    assert job["status"] == "ready", job
    document = service.document(accepted["document_id"])
    assert document["status"] == "ready"
    assert document["evidence_count"] > 0
    hits = service.metadata.search_lexical("Air-Gapped operation", document_id=accepted["document_id"])
    assert hits and hits[0].locator.get("page") == 2
    result = await service.query("What operation is crucial?", "test-session", accepted["document_id"])
    assert result["metadata"]["decision"] == "evidence-query"
    assert result["metadata"]["sources"][0]["document_id"] == accepted["document_id"]


@pytest.mark.asyncio
async def test_query_fails_closed_when_model_does_not_cite_evidence(tmp_path: Path):
    class UngroundedInference(OfflineInference):
        def answer(self, prompt): return "A fluent answer without a source.", {"provider": "offline-test"}
    source_pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")), LocalDocumentParser(), UngroundedInference())
    accepted = await service.import_file(source_pdf.name, str(source_pdf))
    while (job := service.job(accepted["job_id"]))["status"] not in {"ready", "failed"}: await asyncio.sleep(0.05)
    result = await service.query("What is Air-Gapped operation?", "test-session", accepted["document_id"])
    assert result["metadata"]["decision"] == "evidence-extractive-fallback"
    assert "fragmento recuperado" in result["response"]
