import pytest
import asyncio
from pathlib import Path
from app.node.domain import EvidenceUnit
from app.node.parsers import LocalDocumentParser
from app.node.service import NodeService
from app.node.sqlite_store import SQLiteNodeStore
from app.node.storage import LocalSourceStore


class MockInference:
    def answer(self, prompt):
        return "I will speculate on anything.", {"provider": "mock"}


class InMemoryVectorIndex:
    def __init__(self):
        self.items = []

    def upsert(self, evidence):
        self.items.extend(evidence)

    def search(self, query, limit=16, document_id=None):
        return []


@pytest.mark.asyncio
async def test_strict_abstention_when_no_evidence_matches(tmp_path: Path):
    """
    Mission-Critical Sovereign Test: 'Cita o Calla' (Cite or Abstain).
    When scoped to a document, if no passage in the document matches the query,
    the system MUST abstain and refuse to hallucinate an answer.
    """
    store = SQLiteNodeStore(str(tmp_path / "node.db"))
    source_store = LocalSourceStore(str(tmp_path / "sources"))
    parser = LocalDocumentParser()
    service = NodeService(
        store,
        source_store,
        parser,
        MockInference(),
        vector_index=InMemoryVectorIndex(),
    )

    source_pdf = Path(__file__).parent.parent / "docs" / "zyrabit-cioreview-en.pdf"
    accepted = await service.import_file(source_pdf.name, str(source_pdf))
    while (job := service.job(accepted["job_id"]))["status"] not in {"ready", "failed"}:
        await asyncio.sleep(0.05)

    # Query with terms completely absent from the CIO Review document
    result = await service.query(
        "What is the secret recipe for Martian potato stew under Antarctic jurisdiction?",
        "tactical-session",
        accepted["document_id"],
    )

    assert result["metadata"]["decision"] == "abstention-insufficient-evidence"
    assert result["metadata"]["abstention"] is True
    assert result["metadata"]["sources"] == []
    assert "abstención" in result["response"] or "Cita o Calla" in result["response"]
