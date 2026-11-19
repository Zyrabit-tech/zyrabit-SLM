"""Citation format contract: render, tolerant validate, extractive fallback (#207)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.node.domain import EvidenceUnit
from app.node.service import NodeService

UUID = "3a725095-3392-412c-b9c2-a2ada2d9d131"
OTHER = "48c66cf8-1111-2222-3333-444444444444"


def _evidence(identifier: str = UUID) -> EvidenceUnit:
    return EvidenceUnit(
        id=identifier,
        document_id="doc-1",
        content="Proof-of-work anchors the chain against double spending.",
        ordinal=0,
        locator={"page": 1},
        metadata={"filename": "bitcoin.pdf", "score": 0.9},
    )


@pytest.mark.parametrize(
    "answer",
    [
        f"Grounded claim. [EVIDENCE:{UUID}]",
        f"Grounded claim. [EVIDENCE id={UUID}]",
        f"Grounded claim. [EVIDENCE:uuid={UUID}; page=5]",
        f"Grounded claim. [EVIDENCE id={UUID}; bitcoin.pdf; page=1]",
        f"Grounded claim. [EVIDENCE uuid={UUID}]",
    ],
)
def test_validate_grounding_accepts_citation_variants(answer: str):
    ok, cited = NodeService._validate_grounding(answer, [_evidence()])
    assert ok is True
    assert [item.id for item in cited] == [UUID]


@pytest.mark.parametrize(
    "answer",
    [
        f"Wrong id. [EVIDENCE:{OTHER}]",
        f"Truncated. [EVIDENCE:{UUID[:8]}]",
        "No citation at all.",
        f"Internal leak. [EVIDENCE:{UUID}] último pensamiento interno",
    ],
)
def test_validate_grounding_rejects_unknown_or_invalid(answer: str):
    ok, cited = NodeService._validate_grounding(answer, [_evidence()])
    assert ok is False
    assert cited == []


def test_render_evidence_matches_canonical_cite_form():
    rendered = NodeService._render_evidence(_evidence())
    assert rendered.startswith(f"[EVIDENCE:{UUID}]")
    assert "id=" not in rendered.split("\n", 1)[0]
    assert NodeService._EVIDENCE_CITE.search(rendered).group(1) == UUID
    service = NodeService.__new__(NodeService)
    service.identity = None
    prompt = service._prompt("What is proof of work?", rendered, [], None)
    assert f"[EVIDENCE:{UUID}]" in prompt
    assert "[EVIDENCE:uuid]" in prompt  # instruction still names the canonical form


@pytest.mark.asyncio
async def test_extractive_fallback_when_document_selected_and_grounding_fails():
    evidence = [_evidence()]
    service = NodeService.__new__(NodeService)
    service.inference = SimpleNamespace(
        answer=lambda prompt: ("Ungrounded prose about mining.", {"provider": "test"})
    )
    service.metadata = SimpleNamespace(
        get_history=lambda session_id: [],
        get_session_context=lambda session_id: {},
        append_message=lambda *args, **kwargs: None,
        upsert_session_context=lambda *args, **kwargs: None,
    )
    service.identity = None
    service._remember_turn = lambda *args, **kwargs: None

    result = await service._model_response(
        "explica prueba de trabajo",
        "session-1",
        evidence,
        document_id="doc-1",
    )
    assert result["metadata"]["decision"] == "extractive-fallback"
    assert result["metadata"]["rag_hits"] == 1
    assert result["metadata"]["sources"][0]["evidence_id"] == UUID
    assert "Ungrounded prose" not in result["response"]
    assert f"[EVIDENCE:{UUID}]" in result["response"]
    assert "fragmento recuperado" in result["response"]


@pytest.mark.asyncio
async def test_ungrounded_answer_without_document_stays_model_knowledge():
    evidence = [_evidence()]
    service = NodeService.__new__(NodeService)
    service.inference = SimpleNamespace(
        answer=lambda prompt: ("General knowledge reply.", {"provider": "test"})
    )
    service.metadata = SimpleNamespace(
        get_history=lambda session_id: [],
        get_session_context=lambda session_id: {},
        append_message=lambda *args, **kwargs: None,
        upsert_session_context=lambda *args, **kwargs: None,
    )
    service.identity = None
    service._remember_turn = lambda *args, **kwargs: None

    result = await service._model_response(
        "what is a transformer?",
        "session-1",
        evidence,
        document_id=None,
    )
    assert result["metadata"]["decision"] == "model-knowledge"
    assert result["metadata"]["sources"] == []
    assert result["response"] == "General knowledge reply."
