"""Application services for durable import and evidence-bound query."""
from __future__ import annotations

import asyncio
import re
import shutil
import time
import uuid
from pathlib import Path

from app.node.domain import EvidenceUnit, IngestionJob


class NodeService:
    def __init__(self, metadata, source_store, parser, inference, vector_index=None, embedding=None, reranker=None):
        self.metadata = metadata; self.source_store = source_store; self.parser = parser
        self.inference = inference; self.vector_index = vector_index; self.embedding = embedding; self.reranker = reranker
        self._tasks: set[asyncio.Task] = set()

    async def import_file(self, filename: str, staged_path: str) -> dict:
        source = self.source_store.persist(filename, Path(staged_path))
        existing = self.metadata.source_by_hash(source.sha256)
        if existing:
            return {"status": "ready", "deduplicated": True, "source_id": existing["id"], "document_id": self._existing_document(existing["id"])}
        self.metadata.create_source(source)
        document_id, job_id = str(uuid.uuid4()), str(uuid.uuid4())
        self.metadata.create_document(document_id, source.id, type(self.parser).__name__)
        self.metadata.create_job(IngestionJob(job_id, source.id, "queued", "accepted"))
        task = asyncio.create_task(self._process(job_id, document_id, source))
        self._tasks.add(task); task.add_done_callback(self._tasks.discard)
        return {"status": "queued", "job_id": job_id, "source_id": source.id, "document_id": document_id}

    def _existing_document(self, source_id: str) -> str | None:
        # A source hash is immutable, so its latest document is the reusable version.
        import sqlite3
        with sqlite3.connect(self.metadata.path) as conn:
            row = conn.execute("SELECT id FROM node_documents WHERE source_id=? ORDER BY created_at DESC LIMIT 1", (source_id,)).fetchone()
        return row[0] if row else None

    async def _process(self, job_id: str, document_id: str, source) -> None:
        started = time.perf_counter()
        try:
            self.metadata.update_job(job_id, "processing", "extracting")
            self.metadata.set_document_status(document_id, "processing")
            evidence = await asyncio.to_thread(self.parser.parse, source, document_id)
            if not evidence: raise ValueError("No evidence could be extracted from this document")
            self.metadata.update_job(job_id, "processing", "persisting_evidence")
            self.metadata.save_evidence(evidence)
            if self.vector_index:
                self.metadata.update_job(job_id, "processing", "indexing_vectors")
                await asyncio.to_thread(self.vector_index.upsert, evidence)
            self.metadata.set_document_status(document_id, "ready")
            self.metadata.update_job(job_id, "ready", "indexed", metrics={"evidence_units": len(evidence), "elapsed_seconds": round(time.perf_counter() - started, 3)})
        except Exception as exc:
            self.metadata.set_document_status(document_id, "failed", str(exc))
            self.metadata.update_job(job_id, "failed", "failed", error=str(exc), metrics={"elapsed_seconds": round(time.perf_counter() - started, 3)})

    def job(self, job_id: str) -> dict | None: return self.metadata.get_job(job_id)
    def document(self, document_id: str) -> dict | None: return self.metadata.get_document(document_id)
    def documents(self) -> list[dict]: return self.metadata.list_documents()
    def clear_session(self, session_id: str) -> None: self.metadata.clear_history(session_id)

    def capabilities(self) -> list[dict]:
        checks = [("storage", True, "local content store"), ("lexical-index", True, "SQLite FTS5")]
        checks.append(("inference", *self.inference.health()))
        if self.vector_index: checks.append(("vector-index", *self.vector_index.health()))
        else: checks.append(("vector-index", False, "not configured"))
        checks.append(("ocr", bool(shutil.which("tesseract")) and getattr(self.parser, "ocr", None) is not None,
                       "Tesseract local OCR" if getattr(self.parser, "ocr", None) else "disabled by NODE_ENABLE_OCR"))
        checks.append(("reranking", False, "not configured"))
        for name, ok, detail in checks: self.metadata.capability(name, "ready" if ok else "unavailable", detail)
        return self.metadata.capabilities()

    async def query(self, question: str, session_id: str, document_id: str | None = None) -> dict:
        if document_id:
            document = self.metadata.get_document(document_id)
            if not document or document["status"] != "ready":
                return {"response": "El documento seleccionado no está listo para consulta. Espera a que termine su indexación.",
                        "metadata": {"sources": [], "rag_hits": 0, "decision": "selected-document-unavailable"}}
        lexical = self.metadata.search_lexical(question, document_id=document_id)
        vector: list[EvidenceUnit] = []
        if self.vector_index:
            try: vector = await asyncio.to_thread(self.vector_index.search, question, 8, document_id)
            except Exception: vector = []
        evidence: dict[str, EvidenceUnit] = {item.id: item for item in lexical}
        # A vector adapter is not trusted to enforce filtering on our behalf.
        evidence.update({item.id: item for item in vector if not document_id or item.document_id == document_id})
        selected = list(evidence.values())[:6]
        if not selected:
            return {"response": "No encontré evidencia indexada para responder. Selecciona un documento listo o espera a que termine su indexación.", "metadata": {"sources": [], "rag_hits": 0, "decision": "evidence-missing"}}
        context = "\n\n".join(self._render_evidence(item) for item in selected)
        history = self.metadata.get_history(session_id)
        prompt = self._prompt(question, context, history)
        try:
            answer, metrics = await asyncio.to_thread(self.inference.answer, prompt)
        except Exception as exc:
            return {"response": "El motor local no está disponible. Revisa el estado de inferencia y vuelve a intentarlo.", "metadata": {"sources": self._sources(selected), "rag_hits": len(selected), "decision": "inference-unavailable", "error": str(exc)}}
        grounded, cited = self._validate_grounding(answer, selected)
        if not grounded:
            # Fail closed. A fluent answer without references is not a document
            # answer, even if the model happened to receive correct context.
            answer = self._extractive_fallback(selected)
            cited = selected[:1]
            decision = "evidence-extractive-fallback"
        else:
            decision = "evidence-query"
        self.metadata.append_message(session_id, "user", question); self.metadata.append_message(session_id, "assistant", answer)
        return {"response": answer, "metadata": {"sources": self._sources(cited), "rag_hits": len(cited), "decision": decision, **metrics}}

    @staticmethod
    def _validate_grounding(answer: str, evidence: list[EvidenceUnit]) -> tuple[bool, list[EvidenceUnit]]:
        """Accept only model output that cites actual evidence IDs supplied to it."""
        allowed = {item.id: item for item in evidence}
        cited_ids = re.findall(r"\[EVIDENCE:([0-9a-fA-F-]{36})\]", answer)
        if not cited_ids or any(identifier not in allowed for identifier in cited_ids):
            return False, []
        # A model must not disclose chain-of-thought as a side effect of trying
        # to justify itself. This is a product response, not a debug trace.
        lowered = answer.lower()
        if "último pensamiento interno" in lowered or "internal reasoning" in lowered:
            return False, []
        return True, [allowed[identifier] for identifier in dict.fromkeys(cited_ids)]

    @staticmethod
    def _extractive_fallback(evidence: list[EvidenceUnit]) -> str:
        item = evidence[0]
        excerpt = re.sub(r"\s+", " ", item.content).strip()
        if len(excerpt) > 900: excerpt = f"{excerpt[:897].rstrip()}…"
        return f"No puedo verificar una respuesta redactada por el modelo con evidencia trazable. Este es el fragmento recuperado del documento seleccionado:\n\n{excerpt}\n\n[EVIDENCE:{item.id}]"

    @staticmethod
    def _render_evidence(item: EvidenceUnit) -> str:
        location = ", ".join(f"{key}={value}" for key, value in item.locator.items() if value not in (None, False)) or "document"
        return f"[EVIDENCE id={item.id}; {item.metadata.get('filename', 'document')}; {location}]\n{item.content}"

    @staticmethod
    def _sources(evidence: list[EvidenceUnit]) -> list[dict]:
        return [{"evidence_id": item.id, "filename": item.metadata.get("filename"), "document_id": item.document_id,
                 "locator": item.locator, "score": item.metadata.get("score"), "excerpt": item.content[:360]} for item in evidence]

    @staticmethod
    def _prompt(question: str, evidence: str, history: list[dict]) -> str:
        recent = "\n".join(f"{item['role']}: {item['content']}" for item in history[-4:])
        return f"""Responde en el idioma de la pregunta usando exclusivamente la evidencia proporcionada.
No reveles razonamiento interno, conocimiento general, promesas de cumplimiento ni datos no contenidos en la evidencia.
Cada oración declarativa debe terminar con uno o más identificadores exactamente en este formato: [EVIDENCE:uuid].
Usa únicamente IDs incluidos abajo. Si la evidencia no alcanza, responde exactamente: "No encontré evidencia suficiente en el documento seleccionado." seguido de los IDs que sí revisaste.

Conversación reciente:
{recent}

Evidencia:
{evidence}

Pregunta: {question}
"""
