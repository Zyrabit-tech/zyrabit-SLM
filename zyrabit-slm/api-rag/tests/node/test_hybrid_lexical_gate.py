"""Hybrid selection must keep strong vector hits for cross-lingual queries (#208)."""

from __future__ import annotations

from app.node.domain import EvidenceUnit
from app.node.service import NodeService


def _unit(uid: str, document_id: str, content: str, **meta) -> EvidenceUnit:
    return EvidenceUnit(
        id=uid,
        document_id=document_id,
        content=content,
        ordinal=1,
        locator={"page": 1},
        metadata=dict(meta),
    )


def test_instruction_words_are_stripped_from_query_terms() -> None:
    terms = NodeService._query_terms("Resume en viñetas el double spending de Bitcoin")
    assert "resume" not in terms
    assert "vineta" not in terms and "vinetas" not in terms
    assert "bitcoin" in terms


def test_spanish_query_keeps_strong_english_vector_hit() -> None:
    english = _unit(
        "e1",
        "doc-en",
        "Bitcoin solves the double-spending problem with a peer-to-peer timestamped ledger.",
        vector_distance=0.22,
    )
    selected = NodeService(
        metadata=None,  # type: ignore[arg-type]
        source_store=None,  # type: ignore[arg-type]
        parser=None,  # type: ignore[arg-type]
        inference=None,  # type: ignore[arg-type]
    )._select_relevant_evidence(
        "Explica cómo evita el doble gasto",
        lexical=[],
        vector=[english],
        document_id="doc-en",
    )
    assert len(selected) == 1
    assert selected[0].id == "e1"
    assert selected[0].metadata.get("selection") == "vector"


def test_spanish_query_rejects_english_passage_without_vector_or_terms() -> None:
    english = _unit(
        "e1",
        "doc-en",
        "Bitcoin solves the double-spending problem with a peer-to-peer timestamped ledger.",
    )
    selected = NodeService(
        metadata=None,  # type: ignore[arg-type]
        source_store=None,  # type: ignore[arg-type]
        parser=None,  # type: ignore[arg-type]
        inference=None,  # type: ignore[arg-type]
    )._select_relevant_evidence(
        "Explica cómo evita el doble gasto",
        lexical=[english],
        vector=[],
        document_id="doc-en",
    )
    assert selected == []


def test_out_of_domain_weak_vector_hit_still_abstains() -> None:
    weak = _unit(
        "e2",
        "doc-en",
        "Quarterly revenue grew across the Americas and EMEA regions.",
        vector_distance=1.45,
    )
    selected = NodeService(
        metadata=None,  # type: ignore[arg-type]
        source_store=None,  # type: ignore[arg-type]
        parser=None,  # type: ignore[arg-type]
        inference=None,  # type: ignore[arg-type]
    )._select_relevant_evidence(
        "What is the secret recipe for Martian potato stew?",
        lexical=[],
        vector=[weak],
        document_id="doc-en",
    )
    assert selected == []


def test_lexical_matches_still_pass_without_vector() -> None:
    passage = _unit(
        "e3",
        "doc-en",
        "The double-spending problem is solved by a peer-to-peer distributed timestamp server.",
    )
    selected = NodeService(
        metadata=None,  # type: ignore[arg-type]
        source_store=None,  # type: ignore[arg-type]
        parser=None,  # type: ignore[arg-type]
        inference=None,  # type: ignore[arg-type]
    )._select_relevant_evidence(
        "How is the double-spending problem solved?",
        lexical=[passage],
        vector=[],
        document_id="doc-en",
    )
    assert len(selected) == 1
    assert selected[0].metadata.get("selection") == "lexical"
