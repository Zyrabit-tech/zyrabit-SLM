"""Contract: ChromaEvidenceIndex(document_id) must reach VectorStorePort.filter."""
from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.infrastructure.persistence.chroma_adapter import ChromaAdapter
from app.node.adapters import ChromaEvidenceIndex
from app.node.parsers import LocalDocumentParser
from app.node.service import NodeService
from app.node.sqlite_store import SQLiteNodeStore
from app.node.storage import LocalSourceStore
from app.ports.vector_store_port import VectorStorePort
from tests.node.fakes import RecordingVectorStore


def test_vector_store_port_similarity_search_accepts_filter():
    signature = inspect.signature(VectorStorePort.similarity_search)
    assert "filter" in signature.parameters


def test_chroma_adapter_forwards_metadata_filter():
    langchain_chroma = MagicMock()
    langchain_chroma.similarity_search.return_value = []
    adapter = ChromaAdapter(langchain_chroma)

    adapter.similarity_search("air-gapped", k=4, filter={"document_id": "doc-1"})

    langchain_chroma.similarity_search.assert_called_once_with(
        "air-gapped",
        k=4,
        filter={"document_id": "doc-1"},
    )


def test_chroma_evidence_index_passes_document_filter_through_adapter():
    """Real adapter stack: ChromaEvidenceIndex -> ChromaAdapter -> store.filter."""
    store = RecordingVectorStore()
    store.documents = [
        SimpleNamespace(
            page_content="Air-gapped operation requires local inference.",
            metadata={"evidence_id": "ev-1", "document_id": "doc-1", "page": 1},
        ),
        SimpleNamespace(
            page_content="Unrelated document passage.",
            metadata={"evidence_id": "ev-2", "document_id": "doc-2", "page": 1},
        ),
    ]
    index = ChromaEvidenceIndex(ChromaAdapter(store))

    results = index.search("air-gapped", limit=8, document_id="doc-1")

    assert store.calls == [
        {"query_text": "air-gapped", "k": 8, "filter": {"document_id": "doc-1"}}
    ]
    assert [item.id for item in results] == ["ev-1"]
    assert results[0].document_id == "doc-1"


@pytest.mark.asyncio
async def test_vector_search_typeerror_surfaces_lexical_fallback_metadata(tmp_path):
    """If the vector index still rejects filter kwargs, query metadata must say so."""

    class BrokenVectorIndex:
        def upsert(self, evidence):
            pass

        def search(self, query, limit=8, document_id=None):
            # Reproduce the pre-fix adapter signature mismatch.
            raise TypeError("similarity_search() got an unexpected keyword argument 'filter'")

        def delete(self, document_id):
            pass

        def health(self):
            return True, "broken"

    class OfflineInference:
        def answer(self, prompt):
            return "Respuesta lexical de respaldo.", {"provider": "test"}

        def health(self):
            return True, "ok"

    store = SQLiteNodeStore(str(tmp_path / "node.db"))
    service = NodeService(
        store,
        LocalSourceStore(str(tmp_path / "sources")),
        LocalDocumentParser(),
        OfflineInference(),
        vector_index=BrokenVectorIndex(),
        retrieval_mode="hybrid",
    )
    source_pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    accepted = await service.import_file(source_pdf.name, str(source_pdf))
    while (job := service.job(accepted["job_id"]))["status"] not in {"ready", "failed"}:
        await asyncio.sleep(0.05)
    assert job["status"] == "ready", job

    result = await service.query(
        "What is air-gapped operation?",
        "filter-fallback-session",
        accepted["document_id"],
    )

    assert result["metadata"].get("retrieval") == "lexical-fallback"
