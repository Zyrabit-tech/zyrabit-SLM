"""Integration checks for the real, authorized Zyrabit CIO review document."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.node.parsers import LocalDocumentParser
from app.node.service import NodeService
from app.node.sqlite_store import SQLiteNodeStore
from app.node.storage import LocalSourceStore
from tests.node.fakes import InMemoryVectorIndex


class OfflineInference:
    """The import test deliberately does not require a running model."""
    def health(self): return True, "test"
    def answer(self, prompt):
        import re
        evidence_id = re.search(r"id=([0-9a-f-]{36})", prompt).group(1)
        return f"Air-Gapped operation is described as crucial for regulated environments. [EVIDENCE:{evidence_id}]", {"provider": "offline-test"}


class GeneralKnowledgeInference(OfflineInference):
    def answer(self, prompt):
        if "2 * 2" in prompt or "2 × 2" in prompt:
            return "2 × 2 = 4.", {"provider": "offline-test", "latency_seconds": 0.01}
        return super().answer(prompt)


def test_ingestion_etl_normalizes_extractor_artifacts():
    dirty = "\ufeffTítulo\u00a0con\u200b ruido\u00ad\n\n\nTexto\x00 final"
    assert LocalDocumentParser._clean_text(dirty) == "Título con ruido\n\nTexto final"


@pytest.mark.asyncio
async def test_real_cio_review_pdf_is_durable_and_searchable(tmp_path: Path):
    source_pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    assert source_pdf.exists(), "The authorized acceptance PDF must be present"
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")),
                          LocalDocumentParser(), OfflineInference(), vector_index=InMemoryVectorIndex())
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
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")), LocalDocumentParser(), UngroundedInference(), vector_index=InMemoryVectorIndex())
    accepted = await service.import_file(source_pdf.name, str(source_pdf))
    while (job := service.job(accepted["job_id"]))["status"] not in {"ready", "failed"}: await asyncio.sleep(0.05)
    result = await service.query("What is Air-Gapped operation?", "test-session", accepted["document_id"])
    assert result["metadata"]["decision"] == "evidence-extractive-fallback"
    assert "fragmento recuperado" in result["response"]


@pytest.mark.asyncio
async def test_document_is_not_ready_when_vector_index_is_unavailable(tmp_path: Path):
    source_pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")), LocalDocumentParser(), OfflineInference())
    accepted = await service.import_file(source_pdf.name, str(source_pdf))
    while (job := service.job(accepted["job_id"]))["status"] not in {"ready", "failed"}: await asyncio.sleep(0.05)
    assert job["status"] == "failed"
    assert "Vector index is unavailable" in job["error"]


@pytest.mark.asyncio
async def test_reindex_creates_a_new_ready_document_version(tmp_path: Path):
    source_pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")),
                          LocalDocumentParser(), OfflineInference(), vector_index=InMemoryVectorIndex())
    imported = await service.import_file(source_pdf.name, str(source_pdf))
    while (job := service.job(imported["job_id"]))["status"] not in {"ready", "failed"}:
        await asyncio.sleep(0.05)
    assert job["status"] == "ready"

    reindexed = await service.reindex_document(imported["document_id"])
    while (job := service.job(reindexed["job_id"]))["status"] not in {"ready", "failed"}:
        await asyncio.sleep(0.05)
    assert job["status"] == "ready", job
    assert reindexed["document_id"] != imported["document_id"]
    assert service.document(reindexed["document_id"])["version"] == 2
    # An existing browser tab may still have version 1 selected. It must remain
    # scoped to this source by resolving to version 2, never query the corpus.
    result = await service.query("What operation is crucial?", "stale-selection", imported["document_id"])
    assert {source["document_id"] for source in result["metadata"]["sources"]} == {reindexed["document_id"]}


@pytest.mark.asyncio
async def test_explicit_lexical_mode_remains_honest_when_embeddings_are_absent(tmp_path: Path):
    source_pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")),
                          LocalDocumentParser(), OfflineInference(), retrieval_mode="lexical")
    accepted = await service.import_file(source_pdf.name, str(source_pdf))
    while (job := service.job(accepted["job_id"]))["status"] not in {"ready", "failed"}:
        await asyncio.sleep(0.05)
    assert job["status"] == "ready", job
    assert job["metrics"]["retrieval_mode"] == "lexical"
    result = await service.query("What operation is crucial?", "lexical-session", accepted["document_id"])
    assert result["metadata"]["decision"] == "evidence-query-lexical"


@pytest.mark.asyncio
async def test_empty_library_has_a_conversational_start_without_fabricating_evidence(tmp_path: Path):
    class Profile:
        def current(self): return {"assistant_name": "Nora", "user_name": "Abraham Gomez", "tone": "warm", "persona": "document partner"}

    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")),
                          LocalDocumentParser(), OfflineInference(), vector_index=InMemoryVectorIndex(), identity=Profile())
    greeting = await service.query("Hola!", "new-session")
    assert greeting["metadata"]["decision"] == "conversation-greeting"
    assert "Abraham" in greeting["response"]
    assert "Nora" in greeting["response"]

    guidance = await service.query("¿Cómo funciona esto?", "new-session")
    assert guidance["metadata"]["decision"] == "library-empty-guidance"
    assert "importa un archivo" in guidance["response"]


@pytest.mark.asyncio
async def test_greeting_never_runs_retrieval_when_a_document_is_selected(tmp_path: Path):
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")),
                          LocalDocumentParser(), OfflineInference(), vector_index=InMemoryVectorIndex())
    response = await service.query("Hola amigo, ¿cómo estás?", "small-talk", document_id="any-selected-id")
    assert response["metadata"]["decision"] == "conversation-greeting"
    assert response["metadata"]["sources"] == []
    assert "documento activo sigue seleccionado" in response["response"]


@pytest.mark.asyncio
async def test_non_document_question_uses_local_model_not_an_arbitrary_document_chunk(tmp_path: Path):
    service = NodeService(SQLiteNodeStore(str(tmp_path / "node.db")), LocalSourceStore(str(tmp_path / "sources")),
                          LocalDocumentParser(), GeneralKnowledgeInference(), vector_index=InMemoryVectorIndex())
    response = await service.query("Dame la respuesta de 2 * 2", "local-knowledge")
    assert response["response"] == "2 × 2 = 4."
    assert response["metadata"]["decision"] == "model-knowledge"
    assert response["metadata"]["sources"] == []
    assert service._requires_model_knowledge("Dame la respuesta de 2 * 2")
