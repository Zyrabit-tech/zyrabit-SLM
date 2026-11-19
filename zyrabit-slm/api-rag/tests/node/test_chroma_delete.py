"""Ephemeral Chroma contract: delete must remove vectors, never pretend success."""
from __future__ import annotations

import asyncio
from pathlib import Path

import chromadb
import pytest
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import FakeEmbeddings

from app.infrastructure.persistence.chroma_adapter import ChromaAdapter
from app.node.adapters import ChromaEvidenceIndex
from app.node.domain import EvidenceUnit
from app.node.parsers import LocalDocumentParser
from app.node.service import NodeService
from app.node.sqlite_store import SQLiteNodeStore
from app.node.storage import LocalSourceStore
from tests.node.fakes import InMemoryVectorIndex


# Override conftest's autouse infrastructure mocks — this module exercises real Chroma.
@pytest.fixture(autouse=True)
def mock_infrastructure():
    yield {}


class OfflineInference:
    def answer(self, prompt: str):
        return "offline", {}

    def health(self):
        return True, "offline"


class StickyVectorIndex(InMemoryVectorIndex):
    """Simulates a vector backend that silently keeps rows after delete."""

    def delete(self, document_id):
        pass


class VerifyingStickyIndex(StickyVectorIndex):
    """Keeps vectors and raises so NodeService cannot pretend delete succeeded."""

    def delete(self, document_id):
        super().delete(document_id)
        remaining = [e for e in self.evidence if getattr(e, "document_id", None) == document_id]
        if remaining:
            raise RuntimeError(f"vectors remain: {len(remaining)}")


def _ephemeral_index(collection_name: str = "zz_delete_probe") -> tuple[ChromaAdapter, ChromaEvidenceIndex]:
    client = chromadb.EphemeralClient()
    lc = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=FakeEmbeddings(size=16),
    )
    adapter = ChromaAdapter(lc)
    return adapter, ChromaEvidenceIndex(adapter)


def test_chroma_adapter_delete_removes_filtered_vectors():
    adapter, index = _ephemeral_index()
    units = [
        EvidenceUnit("e1", "doc-a", "alpha content", 1, {"page": 1}, {"filename": "a.pdf"}),
        EvidenceUnit("e2", "doc-b", "beta content", 1, {"page": 1}, {"filename": "b.pdf"}),
    ]
    index.upsert(units)
    assert adapter.count(where={"document_id": "doc-a"}) == 1
    assert adapter.count(where={"document_id": "doc-b"}) == 1

    index.delete("doc-a")
    assert adapter.count(where={"document_id": "doc-a"}) == 0
    assert adapter.count(where={"document_id": "doc-b"}) == 1


def test_chroma_adapter_refuses_empty_where_filter():
    adapter, _ = _ephemeral_index("zz_empty_where")
    with pytest.raises(ValueError, match="where filter"):
        adapter.delete({})


def test_chroma_evidence_index_fails_when_vectors_remain():
    adapter, index = _ephemeral_index("zz_sticky_delete")
    index.upsert([EvidenceUnit("e1", "doc-a", "keep me", 1, {"page": 1}, {"filename": "a.pdf"})])

    # Bypass the real delete path so verification must catch remaining rows.
    adapter.delete = lambda where: None  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="vectors remain"):
        index.delete("doc-a")


@pytest.mark.asyncio
async def test_delete_document_propagates_vector_failure(tmp_path: Path):
    source_pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    sticky = VerifyingStickyIndex()
    service = NodeService(
        SQLiteNodeStore(str(tmp_path / "node.db")),
        LocalSourceStore(str(tmp_path / "sources")),
        LocalDocumentParser(),
        OfflineInference(),
        vector_index=sticky,
    )
    accepted = await service.import_file(source_pdf.name, str(source_pdf))
    while (job := service.job(accepted["job_id"]))["status"] not in {"ready", "failed"}:
        await asyncio.sleep(0.05)
    assert job["status"] == "ready"
    doc_id = accepted["document_id"]
    assert len(sticky.evidence) > 0

    with pytest.raises(RuntimeError, match="vectors remain"):
        await service.delete_document(doc_id)

    # Metadata must still exist so the operator can retry after fixing the index.
    assert service.document(doc_id) is not None


@pytest.mark.asyncio
async def test_ephemeral_chroma_delete_document_clears_vectors(tmp_path: Path):
    source_pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    adapter, index = _ephemeral_index("zz_node_delete")
    # Seed one foreign vector so delete must be scoped, not a collection wipe.
    adapter.add_documents(
        [Document(page_content="foreign", metadata={"document_id": "other", "evidence_id": "fx"})]
    )

    service = NodeService(
        SQLiteNodeStore(str(tmp_path / "node.db")),
        LocalSourceStore(str(tmp_path / "sources")),
        LocalDocumentParser(),
        OfflineInference(),
        vector_index=index,
    )
    accepted = await service.import_file(source_pdf.name, str(source_pdf))
    while (job := service.job(accepted["job_id"]))["status"] not in {"ready", "failed"}:
        await asyncio.sleep(0.05)
    assert job["status"] == "ready", job
    doc_id = accepted["document_id"]
    assert adapter.count(where={"document_id": doc_id}) > 0

    assert await service.delete_document(doc_id) is True
    assert service.document(doc_id) is None
    assert adapter.count(where={"document_id": doc_id}) == 0
    assert adapter.count(where={"document_id": "other"}) == 1


@pytest.mark.asyncio
async def test_reindex_removes_previous_document_vectors(tmp_path: Path):
    source_pdf = Path(__file__).parents[2] / "docs" / "zyrabit-cioreview-en.pdf"
    adapter, index = _ephemeral_index("zz_reindex_clean")
    service = NodeService(
        SQLiteNodeStore(str(tmp_path / "node.db")),
        LocalSourceStore(str(tmp_path / "sources")),
        LocalDocumentParser(),
        OfflineInference(),
        vector_index=index,
    )
    imported = await service.import_file(source_pdf.name, str(source_pdf))
    while (job := service.job(imported["job_id"]))["status"] not in {"ready", "failed"}:
        await asyncio.sleep(0.05)
    assert job["status"] == "ready", job
    old_id = imported["document_id"]
    assert adapter.count(where={"document_id": old_id}) > 0

    reindexed = await service.reindex_document(old_id)
    while (job := service.job(reindexed["job_id"]))["status"] not in {"ready", "failed"}:
        await asyncio.sleep(0.05)
    assert job["status"] == "ready", job
    new_id = reindexed["document_id"]
    assert new_id != old_id
    assert adapter.count(where={"document_id": old_id}) == 0
    assert adapter.count(where={"document_id": new_id}) > 0
