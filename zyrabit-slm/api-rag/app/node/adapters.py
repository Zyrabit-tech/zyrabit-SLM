"""Infrastructure adapters for the Node ports."""
from __future__ import annotations

import asyncio
import os
from typing import Sequence

from app.node.domain import EvidenceUnit
from app.ports.inference_port import InferenceRequest


class ExistingInferenceAdapter:
    """Adapts the existing provider family without exposing it to the domain."""
    def __init__(self, provider, model: str):
        self.provider = provider
        self.model = model

    def answer(self, prompt: str) -> tuple[str, dict]:
        messages = None
        if "\nUsuario: " in prompt:
            sys_part, user_part = prompt.rsplit("\nUsuario: ", 1)
            # Remove any trailing assistant prefix from user part if present
            user_part = user_part.split("\nZyra:")[0].split("\nAssistant:")[0].strip()
            messages = [
                {"role": "system", "content": sys_part.strip()},
                {"role": "user", "content": user_part}
            ]
        elif "\nPregunta: " in prompt:
            sys_part, user_part = prompt.rsplit("\nPregunta: ", 1)
            messages = [
                {"role": "system", "content": sys_part.strip()},
                {"role": "user", "content": user_part.strip()}
            ]
        elif "### IDENTIDAD SOBERANA:" in prompt and "### CONSULTA ACTUAL:" in prompt:
            sys_part, user_part = prompt.rsplit("### CONSULTA ACTUAL:", 1)
            messages = [
                {"role": "system", "content": sys_part.strip()},
                {"role": "user", "content": user_part.strip()}
            ]

        temperature = float(os.getenv("INFERENCE_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("INFERENCE_MAX_TOKENS", "1024"))

        req = InferenceRequest(
            model=self.model,
            prompt=prompt,
            messages=messages,
            options={"temperature": temperature, "max_tokens": max_tokens, "repetition_penalty": 1.1}
        )
        result = self.provider.generate(req)
        raw = result.raw_payload or {}
        zyrabit = raw.get("zyrabit") or {}

        ttft_ms = zyrabit.get("ttft_ms")
        if ttft_ms is None:
            p_dur = raw.get("prompt_eval_duration", 0) or 0
            if p_dur > 0:
                ttft_ms = round(p_dur / 1_000_000, 2)
            elif result.latency_seconds and result.latency_seconds > 0:
                ttft_ms = round(result.latency_seconds * 1000 * 0.15, 2)

        tps = zyrabit.get("tps")
        if tps is None:
            e_count = raw.get("eval_count", 0) or 0
            e_dur = raw.get("eval_duration", 0) or 0
            if e_count > 0 and e_dur > 0:
                tps = round(e_count / (e_dur / 1_000_000_000), 2)
            elif result.latency_seconds and result.latency_seconds > 0 and result.text:
                tps = round(len(result.text.split()) / result.latency_seconds, 2)

        target = getattr(result, "execution_target", None) or {
            "engine": zyrabit.get("source", result.provider),
            "device": "cpu_generic" if "docker" in zyrabit.get("mode", "") else "accelerated",
            "backend": zyrabit.get("mode", "standard"),
            "accelerated": zyrabit.get("mode") not in ("docker", "cpu"),
        }

        return result.text, {
            "provider": result.provider,
            "latency_seconds": result.latency_seconds,
            "tps": tps,
            "ttft_ms": ttft_ms,
            "engine": zyrabit.get("engine", result.provider),
            "mode": zyrabit.get("mode"),
            "model": raw.get("model") or self.model,
            "execution_target": target,
            "raw": raw,
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
