"""Infrastructure adapters for the Node ports."""
from __future__ import annotations

import asyncio
from typing import Sequence

from app.node.domain import EvidenceUnit
from app.ports.inference_port import InferenceRequest


class ExistingInferenceAdapter:
    """Adapts the existing provider family without exposing it to the domain."""
    def __init__(self, provider, model: str):
        self.provider = provider
        self.model = model

    def answer(self, prompt: str) -> tuple[str, dict]:
        result = self.provider.generate(InferenceRequest(model=self.model, prompt=prompt, options={"temperature": 0.1, "max_tokens": 700}))
        zyrabit = (result.raw_payload or {}).get("zyrabit") or {}
        return result.text, {
            "provider": result.provider,
            "latency_seconds": result.latency_seconds,
            "tps": zyrabit.get("tps"),
            "ttft_ms": zyrabit.get("ttft_ms"),
            "engine": zyrabit.get("engine"),
            "mode": zyrabit.get("mode"),
            "model": (result.raw_payload or {}).get("model"),
            "raw": result.raw_payload,
        }

    def health(self) -> tuple[bool, str]:
        data = self.provider.health(); return bool(data.get("ok")), str(data.get("reason") or data.get("status", "unknown"))


class ChromaEvidenceIndex:
    """Chroma adapter. It is optional: FTS remains available if it is offline."""
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def upsert(self, evidence: Sequence[EvidenceUnit]) -> None:
        from langchain_core.documents import Document
        documents = [Document(page_content=item.content, metadata={"evidence_id": item.id, "document_id": item.document_id, **item.metadata, **item.locator}) for item in evidence]
        self.vector_store.add_documents(documents)

    def search(self, query: str, limit: int = 8, document_id: str | None = None) -> list[EvidenceUnit]:
        # Metadata filtering is deliberately adapter-specific.
        kwargs = {"k": limit}
        if document_id: kwargs["filter"] = {"document_id": document_id}
        results = self.vector_store.similarity_search(query, **kwargs)
        output = []
        for ordinal, item in enumerate(results, start=1):
            metadata = item.metadata
            evidence_id = metadata.get("evidence_id")
            if evidence_id and (not document_id or metadata.get("document_id") == document_id):
                output.append(EvidenceUnit(evidence_id, metadata.get("document_id", ""), item.page_content, ordinal,
                    {key: metadata[key] for key in ("page", "sheet", "range", "slide", "paragraph", "table") if key in metadata}, metadata))
        return output

    def health(self) -> tuple[bool, str]:
        try: return bool(self.vector_store.heartbeat()), "connected"
        except Exception as exc: return False, str(exc)


class DisabledCapability:
    def __init__(self, detail: str = "not configured"):
        self.detail = detail
    def health(self) -> tuple[bool, str]: return False, self.detail


class SovereignProfileIdentity:
    """Reads the local profile at response time so settings take effect immediately."""
    def current(self) -> dict:
        from app.infrastructure.shared.state_tracker import SovereignStateManager
        profile = SovereignStateManager.get_user_profile() or {}
        return {
            "assistant_name": str(profile.get("assistant_name") or "Zyra").strip()[:48],
            "user_name": str(profile.get("name") or "").strip()[:80],
            "tone": str(profile.get("tone") or "clear").strip().lower(),
            "persona": str(profile.get("persona") or "document analyst").strip().lower(),
        }
