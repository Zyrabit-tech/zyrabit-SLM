"""Application services for durable import and evidence-bound query."""
from __future__ import annotations

import asyncio
import re
import shutil
import time
import unicodedata
import uuid
from pathlib import Path

from app.node.domain import EvidenceUnit, IngestionJob


class NodeService:
    def __init__(self, metadata, source_store, parser, inference, vector_index=None, embedding=None, reranker=None, retrieval_mode: str = "hybrid", identity=None):
        self.metadata = metadata; self.source_store = source_store; self.parser = parser
        self.inference = inference; self.vector_index = vector_index; self.embedding = embedding; self.reranker = reranker
        self.identity = identity
        if retrieval_mode not in {"hybrid", "lexical"}:
            raise ValueError("retrieval_mode must be 'hybrid' or 'lexical'")
        self.retrieval_mode = retrieval_mode
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

    async def reindex_document(self, document_id: str) -> dict:
        source_row = self.metadata.source_for_document(document_id)
        if not source_row:
            raise ValueError("Document not found")
        source = self.source_store.persist(source_row["filename"], Path(source_row["stored_path"]))
        # Preserve the original source identity; reindexing is a new document
        # version, not a new import.
        source = source.__class__(**{**source.__dict__, "id": source_row["id"]})
        new_document_id, job_id = str(uuid.uuid4()), str(uuid.uuid4())
        self.metadata.create_document(new_document_id, source.id, type(self.parser).__name__)
        self.metadata.create_job(IngestionJob(job_id, source.id, "queued", "reindex-accepted"))
        task = asyncio.create_task(self._process(job_id, new_document_id, source))
        self._tasks.add(task); task.add_done_callback(self._tasks.discard)
        return {"status": "queued", "job_id": job_id, "source_id": source.id, "document_id": new_document_id, "reindexed_from": document_id}

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
            if self.retrieval_mode == "hybrid" and self.embedding:
                embedding_ok, embedding_detail = self.embedding.health()
                if not embedding_ok:
                    raise RuntimeError(f"Embedding provider is unavailable: {embedding_detail}")
            if self.retrieval_mode == "hybrid" and not self.vector_index:
                raise RuntimeError("Vector index is unavailable. Document was preserved but is not ready for retrieval.")
            if self.retrieval_mode == "hybrid":
                self.metadata.update_job(job_id, "processing", "indexing_vectors")
                await asyncio.to_thread(self.vector_index.upsert, evidence)
            self.metadata.set_document_status(document_id, "ready")
            self.metadata.update_job(job_id, "ready", "indexed", metrics={"evidence_units": len(evidence), "retrieval_mode": self.retrieval_mode, "elapsed_seconds": round(time.perf_counter() - started, 3)})
        except Exception as exc:
            self.metadata.set_document_status(document_id, "failed", str(exc))
            self.metadata.update_job(job_id, "failed", "failed", error=str(exc), metrics={"elapsed_seconds": round(time.perf_counter() - started, 3)})

    def job(self, job_id: str) -> dict | None: return self.metadata.get_job(job_id)
    def document(self, document_id: str) -> dict | None: return self.metadata.get_document(document_id)
    def documents(self) -> list[dict]: return self.metadata.list_documents()
    def clear_session(self, session_id: str) -> None: self.metadata.clear_history(session_id)

    def capabilities(self) -> list[dict]:
        checks = [("storage", True, "local content store"), ("lexical-index", True, "SQLite FTS5"), ("retrieval-mode", True, self.retrieval_mode)]
        checks.append(("inference", *self.inference.health()))
        if self.retrieval_mode == "lexical": checks.append(("embeddings", True, "not required in explicit lexical mode"))
        elif self.embedding: checks.append(("embeddings", *self.embedding.health()))
        else: checks.append(("embeddings", False, "not configured"))
        if self.vector_index: checks.append(("vector-index", *self.vector_index.health()))
        else: checks.append(("vector-index", False, "not configured"))
        checks.append(("ocr", bool(shutil.which("tesseract")) and getattr(self.parser, "ocr", None) is not None,
                       "Tesseract local OCR" if getattr(self.parser, "ocr", None) else "disabled by NODE_ENABLE_OCR"))
        checks.append(("reranking", False, "not configured"))
        for name, ok, detail in checks: self.metadata.capability(name, "ready" if ok else "unavailable", detail)
        return self.metadata.capabilities()

    async def query(self, question: str, session_id: str, document_id: str | None = None) -> dict:
        conversational = self._conversational_response(question, bool(document_id))
        if conversational:
            self.metadata.append_message(session_id, "user", question)
            self.metadata.append_message(session_id, "assistant", conversational["response"])
            return conversational
        if self._requires_model_knowledge(question):
            return await self._model_knowledge_response(question, session_id)
        if document_id:
            document = self.metadata.get_document(document_id)
            replacement = self.metadata.latest_ready_document_for(document_id) if document else None
            if replacement:
                # A reindex creates immutable versions. Existing UI sessions
                # always follow the newest ready version of the same source so
                # they neither fail nor accidentally escape to the full corpus.
                document_id = replacement["id"]
            elif not document or document["status"] != "ready":
                return {"response": "El documento seleccionado aún no está listo. En la biblioteca verás **Indexed and ready** cuando pueda responder con fuentes; si falló, vuelve a indexarlo desde su detalle.",
                        "metadata": {"sources": [], "rag_hits": 0, "decision": "selected-document-unavailable"}}
        lexical = self.metadata.search_lexical(question, document_id=document_id)
        # A vector-only hit is not enough to claim a document answered a
        # question. Small local models otherwise retrieve arbitrary passages
        # for arithmetic and other non-document questions.
        if not lexical:
            return await self._model_knowledge_response(question, session_id)
        vector: list[EvidenceUnit] = []
        if self.retrieval_mode == "hybrid" and self.vector_index:
            try: vector = await asyncio.to_thread(self.vector_index.search, question, 8, document_id)
            except Exception: vector = []
        evidence: dict[str, EvidenceUnit] = {item.id: item for item in lexical}
        # A vector adapter is not trusted to enforce filtering on our behalf.
        evidence.update({item.id: item for item in vector if not document_id or item.document_id == document_id})
        selected = list(evidence.values())[:6]
        if not selected:
            return await self._model_knowledge_response(question, session_id)
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
            decision = "evidence-query" if self.retrieval_mode == "hybrid" else "evidence-query-lexical"
        self.metadata.append_message(session_id, "user", question); self.metadata.append_message(session_id, "assistant", answer)
        return {"response": answer, "metadata": {"sources": self._sources(cited), "rag_hits": len(cited), "decision": decision, **metrics}}

    @staticmethod
    def _requires_model_knowledge(question: str) -> bool:
        """Route unambiguously non-document questions before retrieval.

        This is deliberately narrow. It prevents obvious arithmetic from being
        falsely attributed to a random document passage while leaving document
        questions to retrieval and future reranking.
        """
        normalized = unicodedata.normalize("NFKD", question).encode("ascii", "ignore").decode().lower()
        return bool(re.search(r"(?<!\w)\d+(?:\.\d+)?\s*(?:\+|\-|\*|x|×|/|÷)\s*\d+(?:\.\d+)?(?!\w)", normalized))

    async def _model_knowledge_response(self, question: str, session_id: str) -> dict:
        """Answer outside the corpus without laundering it as a document claim."""
        identity = self._identity()
        prompt = f"""You are {identity['assistant_name']}, a local assistant. Answer the user's question in its language using your own local model knowledge.
Do not claim that the answer comes from uploaded documents. Be concise, helpful and direct. Do not reveal internal reasoning.
Use clean Markdown: a short direct answer first, then at most three bullets only when they improve clarity. Never output internal tags or source identifiers.

Question: {question}
"""
        try:
            answer, metrics = await asyncio.to_thread(self.inference.answer, prompt)
        except Exception:
            return self._no_evidence_response(question)
        self.metadata.append_message(session_id, "user", question)
        self.metadata.append_message(session_id, "assistant", answer)
        return {"response": answer, "metadata": {"sources": [], "rag_hits": 0, "decision": "model-knowledge", **metrics}}

    def _conversational_response(self, question: str, has_active_document: bool) -> dict | None:
        """Handle short human turns before retrieval; never turn a greeting into a citation."""
        normalized = unicodedata.normalize("NFKD", question).encode("ascii", "ignore").decode().lower().strip()
        normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        identity = self._identity()
        user = f" {identity['user_name'].split()[0]}" if identity["user_name"] else ""
        assistant = identity["assistant_name"]
        metadata = {"sources": [], "rag_hits": 0, "decision": "conversation-greeting"}

        greeting = r"(?:hola|buenas|hello|hi|hey)(?: amigo| amiga)?(?: como estas| como va| que tal)?"
        if re.fullmatch(greeting, normalized) or re.fullmatch(r"como estas", normalized):
            focus = "El documento activo sigue seleccionado; dime qué quieres revisar y lo buscamos con sus páginas fuente." if has_active_document else "Cuando quieras, sube o selecciona un documento y lo revisamos con fuentes verificables."
            return {"response": f"Todo en orden{user}. Soy {assistant}, listo para trabajar contigo. {focus}", "metadata": metadata}

        if re.fullmatch(r"(gracias|muchas gracias|perfecto|ok|vale|va)", normalized):
            return {"response": f"Claro{user}. Seguimos cuando quieras; si hacemos una consulta documental, te diré exactamente de qué archivo y página sale.", "metadata": {**metadata, "decision": "conversation-acknowledgement"}}
        return None

    def _no_evidence_response(self, question: str) -> dict:
        """Give product guidance without pretending an ungrounded answer is RAG."""
        normalized = unicodedata.normalize("NFKD", question).encode("ascii", "ignore").decode().lower().strip()
        documents = self.documents()
        ready = [document for document in documents if document.get("status") == "ready"]
        metadata = {"sources": [], "rag_hits": 0}
        identity = self._identity()
        assistant = identity["assistant_name"]
        user = f" {identity['user_name'].split()[0]}" if identity["user_name"] else ""

        if re.fullmatch(r"(hola|buenas|hello|hi|hey)[!. ]*", normalized):
            return {
                "response": f"Hola{user}. Soy {assistant}. Aquí trabajamos con documentos locales: tú subes el archivo y yo te ayudo a encontrar lo importante, siempre con una fuente que puedas revisar.",
                "metadata": {**metadata, "decision": "library-empty-greeting"},
            }
        if not documents:
            if re.search(r"\b(como|como funciona|que hago|ayuda)\b", normalized):
                response = f"Va{user}. El flujo es corto: importa un archivo, espera a que quede **Indexed and ready**, selecciónalo y pregúntame algo concreto. Yo te responderé con el pasaje y la página, no con suposiciones. Cuando tengas el primer documento, empezamos."
            else:
                response = f"Todavía no tengo documentos contigo{user}. Importa uno y, cuando esté listo, puedo resumirlo, encontrar decisiones o responder preguntas con páginas fuente. Si quieres, empieza con el archivo que más te urge entender."
            return {
                "response": response,
                "metadata": {**metadata, "decision": "library-empty-guidance"},
            }
        if not ready:
            return {
                "response": "Ya recibí archivos, pero todavía no hay uno listo para consultar. Espera a que la importación termine; si falla, abre el estado del documento para ver el diagnóstico y vuelve a indexarlo.",
                "metadata": {**metadata, "decision": "library-indexing-guidance"},
            }
        return {
            "response": f"No encontré un pasaje que sostenga esa respuesta, {user.strip() or 'por ahora'}. Probemos con palabras del documento o elige otro archivo listo. Prefiero decirte eso antes que completar huecos con una respuesta inventada.",
            "metadata": {**metadata, "decision": "evidence-not-found"},
        }

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

    def _identity(self) -> dict:
        profile = self.identity.current() if self.identity else {}
        return {
            "assistant_name": profile.get("assistant_name") or "Zyra",
            "user_name": profile.get("user_name") or "",
            "tone": profile.get("tone") or "clear",
            "persona": profile.get("persona") or "document analyst",
        }

    def _prompt(self, question: str, evidence: str, history: list[dict]) -> str:
        recent = "\n".join(f"{item['role']}: {item['content']}" for item in history[-4:])
        identity = self._identity()
        return f"""Responde en el idioma de la pregunta usando exclusivamente la evidencia proporcionada.
No reveles razonamiento interno, conocimiento general, promesas de cumplimiento ni datos no contenidos en la evidencia.
Cada oración declarativa debe terminar con uno o más identificadores exactamente en este formato: [EVIDENCE:uuid].
Usa únicamente IDs incluidos abajo. Si la evidencia no alcanza, responde exactamente: "No encontré evidencia suficiente en el documento seleccionado." seguido de los IDs que sí revisaste.
Eres {identity['assistant_name']}, un {identity['persona']} con tono {identity['tone']}: sé directo, humano y breve. La voz nunca sustituye evidencia ni menciona una fuente que no esté abajo.
Usa Markdown limpio: una respuesta breve primero y listas sólo cuando aclaren pasos o hechos. No uses caracteres de control ni identificadores fuera de las citas requeridas.

Conversación reciente:
{recent}

Evidencia:
{evidence}

Pregunta: {question}
"""
