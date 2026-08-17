"""Application services for durable import and evidence-bound query."""
from __future__ import annotations

import asyncio
import re
import shutil
import time
import unicodedata
import uuid
from dataclasses import replace
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
    def session(self, session_id: str) -> dict:
        return {"messages": self.metadata.session_history(session_id), "context": self.metadata.get_session_context(session_id)}
    def session_history(self, session_id: str) -> list[dict]: return self.session(session_id)["messages"]
    def update_session_context(self, session_id: str, active_document_id: str | None = None) -> dict:
        document_id = self._resolve_document_scope(active_document_id)
        source_id = None
        if document_id:
            document = self.metadata.get_document(document_id)
            source_id = document.get("source_id") if document else None
        return self.metadata.upsert_session_context(session_id, active_document_id=document_id, active_source_id=source_id)

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
        session_context = self.metadata.get_session_context(session_id)
        document_id = self._resolve_document_scope(document_id or session_context.get("active_document_id"))
        if document_id != session_context.get("active_document_id"):
            session_context = self.update_session_context(session_id, document_id)
        effective_question = self._effective_question(question, session_context)
        rag_t0 = time.time()
        if not document_id and self._is_conversational(effective_question):
            selected = []
            rag_retrieval_ms = 0.0
        else:
            lexical = self.metadata.search_lexical(effective_question, limit=16, document_id=document_id)
            vector: list[EvidenceUnit] = []
            if self.retrieval_mode == "hybrid" and self.vector_index:
                try: vector = await asyncio.to_thread(self.vector_index.search, effective_question, 16, document_id)
                except Exception: vector = []
            selected = self._select_relevant_evidence(effective_question, lexical, vector, document_id)
            rag_retrieval_ms = round((time.time() - rag_t0) * 1000, 2)
        return await self._model_response(question, session_id, selected, document_id, session_context, rag_retrieval_ms=rag_retrieval_ms)

    @staticmethod
    def _is_conversational(question: str) -> bool:
        normalized = unicodedata.normalize("NFKD", question).encode("ascii", "ignore").decode().lower().strip()
        if re.search(r"\b(hola|buenas|hello|hi|hey|que tal|como estas|quien eres|que eres|que haces|que puedes|presenta\w*|ayud\w*|cuenta\w*|gracia\w*|adios|bye)\b", normalized):
            if not re.search(r"\b(documento|archivo|pdf|pagina|contrato|manual|texto|doc|fuente)\b", normalized):
                return True
        return False

    def _resolve_document_scope(self, document_id: str | None) -> str | None:
        if not document_id:
            return None
        document = self.metadata.get_document(document_id)
        replacement = self.metadata.latest_ready_document_for(document_id) if document else None
        if replacement:
            return replacement["id"]
        if not document or document["status"] != "ready":
            return None
        return document_id

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
        """Compatibility wrapper for callers outside the Node query pipeline."""
        return await self._model_response(question, session_id, [])

    async def _model_response(self, question: str, session_id: str, evidence: list[EvidenceUnit], document_id: str | None = None, session_context: dict | None = None, rag_retrieval_ms: float = 0.0) -> dict:
        """Generate one answer from model knowledge plus bounded local evidence."""
        identity = self._identity()
        context = self._bounded_context(evidence)
        history = self.metadata.get_history(session_id)
        session_context = session_context or self.metadata.get_session_context(session_id)
        prompt = self._prompt(question, context, history, session_context)
        try:
            answer, metrics = await asyncio.to_thread(self.inference.answer, prompt)
        except Exception:
            return self._no_evidence_response(question)
        grounded, cited = self._validate_grounding(answer, evidence)
        decision = "model-with-evidence" if grounded else "model-knowledge"
        metadata = {
            "sources": self._sources(cited),
            "rag_hits": len(cited),
            "context_hits": len(evidence),
            "rag_retrieval_ms": rag_retrieval_ms,
            "decision": decision,
            **metrics
        }
        self.metadata.append_message(session_id, "user", question, document_id=document_id)
        self.metadata.append_message(session_id, "assistant", answer, metadata=metadata, document_id=document_id)
        self._remember_turn(session_id, question, answer, cited, document_id, session_context)
        return {"response": answer, "metadata": metadata}

    def _conversational_response(self, question: str, has_active_document: bool) -> dict | None:
        """Handle short human turns before retrieval; never turn a greeting into a citation."""
        normalized = unicodedata.normalize("NFKD", question).encode("ascii", "ignore").decode().lower().strip()
        normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        identity = self._identity()
        user = f" {identity['user_name'].split()[0]}" if identity["user_name"] else ""
        assistant = identity["assistant_name"]
        metadata = {"sources": [], "rag_hits": 0, "decision": "conversation-greeting"}

        # Short social turns must never enter retrieval.  A document can easily
        # contain common words such as "hola" or "otra", which used to make a
        # natural greeting look like a document question.
        greeting = r"(?:hola|buenas|hello|hi|hey)(?: (?:amigo|amiga|man|bro|hermano|papa|vato|compa))?(?: (?:como estas|como va|que tal))?"
        assistant_token = unicodedata.normalize("NFKD", assistant).encode("ascii", "ignore").decode().lower()
        addressed_greeting = re.fullmatch(rf"(?:hola|buenas|hello|hi|hey) {re.escape(assistant_token)}", normalized)
        if re.fullmatch(greeting, normalized) or addressed_greeting or re.fullmatch(r"como estas", normalized):
            focus = "El documento activo sigue seleccionado; dime qué quieres revisar y lo buscamos con sus páginas fuente." if has_active_document else "Cuando quieras, sube o selecciona un documento y lo revisamos con fuentes verificables."
            return {"response": f"Todo en orden{user}. Soy {assistant}, listo para trabajar contigo. {focus}", "metadata": metadata}

        is_short_clarification = (
            re.fullmatch(r"(?:otra vez|como|como asi|que onda|que paso|una pregunta)", normalized)
            or (normalized.startswith("como una pregunta") and len(normalized.split()) <= 8)
        )
        if is_short_clarification:
            return {
                "response": "Tienes razón. Eso no era una consulta documental y no debí buscar un pasaje. Háblame normal: para conversar no necesito fuentes; cuando me preguntes por un archivo, entonces sí te responderé con sus páginas.",
                "metadata": {**metadata, "decision": "conversation-clarification"},
            }

        if re.fullmatch(r"(?:chingado|chale|rayos|carajo|no manches)", normalized):
            return {
                "response": "Sí, estuvo mal. Ya no voy a convertir una conversación en una búsqueda de documentos. Dime la pregunta y te respondo directo; si el archivo aporta algo, lo sumaré con sus fuentes.",
                "metadata": {**metadata, "decision": "conversation-clarification"},
            }

        if re.fullmatch(r"(?:tu dime|tu que dices|que me dices)", normalized):
            return {
                "response": "Tú marcas el rumbo. Podemos platicar normal, revisar un documento específico o comparar varios; cuando haya evidencia útil, te diré de dónde salió sin interrumpir la conversación.",
                "metadata": {**metadata, "decision": "conversation-clarification"},
            }

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
    def _query_terms(question: str) -> set[str]:
        """Keep only meaningful terms for a conservative local relevance gate."""
        stop_words = {
            "a", "al", "algo", "con", "como", "cual", "cuando", "de", "del", "dame", "el", "en", "es", "esta", "este",
            "la", "las", "lo", "los", "me", "mi", "para", "por", "que", "quiero", "se", "sobre", "su", "un", "una", "y",
            "hola", "buenas", "hello", "hey", "gracias", "amigo", "amiga", "man", "bro", "papa", "vato", "compa",
            "otra", "vez", "chingado", "chale", "rayos", "carajo", "dime", "zyra",
            "explain", "better", "more", "that", "this", "again", "continue",
            "and", "are", "do", "for", "how", "is", "of", "the", "to", "what", "which", "with",
        }
        normalized = unicodedata.normalize("NFKD", question).encode("ascii", "ignore").decode().lower()
        return {token.rstrip("s") for token in re.findall(r"[a-z0-9]{3,}", normalized) if token not in stop_words}

    @staticmethod
    def _is_general_knowledge_question(question: str) -> bool:
        normalized = unicodedata.normalize("NFKD", question).encode("ascii", "ignore").decode().lower()
        asks_for_document = bool(re.search(r"\b(documento|archivo|pdf|pagina|pagina|clausula|contrato|playbook|propuesta|manual|este doc)\b", normalized))
        technical_topic = bool(re.search(r"\b(transformer|token(?:es)?|internet|ia|inteligencia artificial|programacion|python|algoritmo)\b", normalized))
        return technical_topic and not asks_for_document

    def _select_relevant_evidence(self, question: str, lexical: list[EvidenceUnit], vector: list[EvidenceUnit], document_id: str | None) -> list[EvidenceUnit]:
        """Rank retrieved candidates and keep only evidence with textual support."""
        terms = self._query_terms(question)
        if not terms:
            return []
        required_matches = min(3, max(1, (len(terms) + 1) // 2))
        if len(terms) == 1 and not document_id:
            required_matches = 2

        def match_count(item: EvidenceUnit) -> int:
            text = unicodedata.normalize("NFKD", item.content).encode("ascii", "ignore").decode().lower()
            return sum(term in text for term in terms)

        fused: dict[str, tuple[EvidenceUnit, float]] = {}
        for rank, item in enumerate(lexical, start=1):
            fused[item.id] = (item, fused.get(item.id, (item, 0.0))[1] + 1 / (60 + rank))
        for rank, item in enumerate(vector, start=1):
            fused[item.id] = (item, fused.get(item.id, (item, 0.0))[1] + 1 / (60 + rank))

        ranked = sorted(fused.values(), key=lambda pair: (match_count(pair[0]), pair[1]), reverse=True)
        candidates: list[EvidenceUnit] = []
        for item, score in ranked:
            if document_id and item.document_id != document_id:
                continue
            matches = match_count(item)
            if matches < required_matches:
                continue
            candidates.append(replace(item, metadata={**item.metadata, "score": item.metadata.get("score", score), "matches": matches}))
            if len(candidates) == 4:
                break
        return candidates

    def _effective_question(self, question: str, session_context: dict) -> str:
        if not self._is_followup(question):
            return question
        prior = session_context.get("last_user_intent") or session_context.get("conversation_summary") or ""
        if not prior:
            return question
        return f"{prior}\nFollow-up actual: {question}"

    @staticmethod
    def _is_followup(question: str) -> bool:
        normalized = unicodedata.normalize("NFKD", question).encode("ascii", "ignore").decode().lower().strip()
        normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if len(normalized.split()) <= 4 and re.search(r"\b(eso|esto|como|porque|dame mas|mas|explica|explain|better|more|that|this|again|sigue|continua|continue|otra vez)\b", normalized):
            return True
        return bool(re.fullmatch(r"(?:como|como asi|por que|porque|dame mas|explicalo|explain that better|tell me more|sigue|continua|continue|y eso|eso)", normalized))

    def _remember_turn(self, session_id: str, question: str, answer: str, evidence: list[EvidenceUnit], document_id: str | None, session_context: dict) -> None:
        current_summary = session_context.get("conversation_summary") or ""
        next_summary = self._compact_summary(current_summary, question, answer, document_id)
        active_source_id = session_context.get("active_source_id")
        if document_id:
            document = self.metadata.get_document(document_id)
            active_source_id = document.get("source_id") if document else active_source_id
        self.metadata.upsert_session_context(
            session_id,
            active_document_id=document_id or session_context.get("active_document_id"),
            active_source_id=active_source_id,
            last_evidence_ids=[item.id for item in evidence],
            last_user_intent=question,
            conversation_summary=next_summary,
        )

    @staticmethod
    def _compact_summary(current: str, question: str, answer: str, document_id: str | None) -> str:
        clean_question = re.sub(r"\s+", " ", question).strip()
        clean_answer = re.sub(r"\s+", " ", re.sub(r"\[EVIDENCE:[0-9a-fA-F-]{36}\]", "", answer)).strip()
        if len(clean_answer) > 220:
            clean_answer = f"{clean_answer[:217].rstrip()}..."
        entry = f"Usuario: {clean_question}. Respuesta: {clean_answer}"
        if document_id:
            entry = f"Documento activo {document_id}. {entry}"
        combined = f"{current}\n{entry}".strip() if current else entry
        return combined[-1_200:]

    def _bounded_context(self, evidence: list[EvidenceUnit]) -> str:
        """Prevent documents or history from filling the inference context window."""
        remaining = 5_400
        blocks: list[str] = []
        for item in evidence:
            content = re.sub(r"\s+", " ", item.content).strip()
            block = self._render_evidence(item).replace(item.content, content)
            if len(block) > remaining:
                block = f"{block[:remaining - 1].rstrip()}…"
            if not block:
                break
            blocks.append(block)
            remaining -= len(block)
            if remaining <= 0:
                break
        return "\n\n".join(blocks)

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

    def _prompt(self, question: str, evidence: str, history: list[dict], session_context: dict | None = None) -> str:
        identity = self._identity()
        if not evidence:
            recent = "\n".join(f"{item['role']}: {str(item['content'])[:250]}" for item in history[-2:])
            history_block = f"\nConversación previa:\n{recent}\n" if recent else ""
            return f"""Eres {identity['assistant_name']}, un asistente soberano inteligente, útil y claro con tono {identity['tone']}.
Responde de manera natural, amable y directa a la consulta o conversación del usuario en su idioma.{history_block}
Pregunta: {question}"""

        recent = "\n".join(f"{item['role']}: {str(item['content'])[:450]}" for item in history[-3:])
        evidence_rule = "Hay evidencia local recuperada abajo. Úsala para responder con precisión. Si una afirmación depende de esa evidencia, añade al final del párrafo el identificador [EVIDENCE:uuid] correspondiente. No inventes contenido."
        return f"""Eres {identity['assistant_name']}, un {identity['persona']} local con tono {identity['tone']}.
La última pregunta del usuario es la instrucción prioritaria: respóndela directamente usando la evidencia local recuperada.
{evidence_rule}

Conversación reciente:
{recent}

Evidencia local:
{evidence}

Pregunta: {question}"""
