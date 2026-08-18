import os
import re
import time
from typing import Optional, Dict, Any

from app.domain.ports.telemetry_port import TelemetryPort
from app.infrastructure.shared.config import MODEL_NAME
from app.infrastructure.shared.state_tracker import SovereignStateManager
from app.domain.services.context_manager import ContextManager
from app.ports.inference_port import InferenceRequest


def _citation_label(metadata: dict) -> str:
    """Return a user-facing source label without leaking local paths."""
    filename = os.path.basename(str(metadata.get("source", "unknown")))
    page = metadata.get("page")
    return f"{filename} · p. {page}" if page else filename

class ChatUseCase:
    """
    V5.0 Brain: Orchestrates Security, Hybrid RAG, and Inference.
    """
    def __init__(
        self, 
        inference_provider, 
        retriever_service, 
        gatekeeper, 
        cache, 
        telemetry: TelemetryPort,
        reranker = None,
        memory_manager = None,
        streaming_provider = None,
        mcp_client = None
    ):
        self.inference_provider = inference_provider
        self.retriever_service = retriever_service
        self.gatekeeper = gatekeeper
        self.cache = cache
        self.telemetry = telemetry
        self.context_manager = ContextManager()
        self.reranker = reranker
        self.memory_manager = memory_manager
        self.streaming_provider = streaming_provider
        self.mcp_client = mcp_client

    async def execute(self, text: str, client_msg_id: Optional[str] = None, history: Optional[list] = None, source: str = "WEB", provider: Optional[str] = None) -> Dict[str, Any]:
        try:
            # 0. Idempotency Check
            if client_msg_id:
                cached_res = self.cache.get(client_msg_id)
                if cached_res:
                    cached_res["metadata"]["cached"] = True
                    return cached_res

            # 1. Security Check (PII Masking)
            sanitized_text, entities = self.gatekeeper.mask_pii(text)
            self.telemetry.log_security_audit(sanitized_text)
            
            if any(entities.values()):
                found = [k for k, v in entities.items() if v]
                self.telemetry.log_security_audit(
                    f"PII detected ({found}): {sanitized_text}"
                )
            
            # 2. Routing Decision
            decision = self.gatekeeper.get_routing_decision(sanitized_text)
            
            if decision == "reject":
                return {
                    "response": "I'm sorry, that query is out of scope.",
                    "metadata": {"decision": "rejected", "cached": False}
                }

            # 3. Hybrid Context Retrieval (RAG)
            sources = []
            results = []  # ensure always defined for build_final_prompt
            rag_retrieval_ms = 0.0
            if decision == "rag":
                if not self.retriever_service:
                    decision = "direct (no-retriever)"
                else:
                    try:
                        rag_t0 = time.time()
                        results = await self.retriever_service.search(sanitized_text)
                        rag_retrieval_ms = round((time.time() - rag_t0) * 1000, 2)
                        # The UI injects the selected filename into the question.
                        # Preserve that scope so unrelated documents cannot pollute
                        # an answer that is meant to be grounded in one file.
                        referenced_files = re.findall(
                            r"[\w.-]+\.(?:pdf|docx|md|txt)", sanitized_text,
                            flags=re.IGNORECASE,
                        )
                        if referenced_files:
                            selected_filename = os.path.basename(referenced_files[-1]).lower()
                            scoped_results = [
                                doc for doc in results
                                if os.path.basename(str(doc.metadata.get("source", ""))).lower() == selected_filename
                            ]
                            if scoped_results:
                                results = scoped_results
                        if results:
                            if self.reranker:
                                # Advanced RAG: Re-Rank candidates and filter
                                ranked_docs = self.reranker.rerank(sanitized_text, results)
                                reranked_results = [doc for doc, score in ranked_docs if score >= 0.6][:3]
                                # A missing local reranker model or a conservative score
                                # must not erase valid retrieval evidence.
                                results = reranked_results or results[:3]
                            else:
                                results = results[:3]
                                
                            if results:
                                sources = list(dict.fromkeys(
                                    _citation_label(r.metadata) for r in results
                                ))
                    except Exception as e:
                        self.telemetry.log_security_audit(f"RAG search failed: {e}")
                        decision = "direct (fallback)"

            # 4. Inference
            # Load system prompt from user profile, fallback to default
            user_profile = SovereignStateManager.get_user_profile()
            system_prompt = (user_profile.get("system_prompt") or "").strip() or "Eres Zyra, un asistente soberano inteligente, útil y conciso. Responde siempre de manera natural y clara en el idioma del usuario."

            # 4. Memory Recovery
            if history is None:
                history = SovereignStateManager.get_history(client_msg_id or "default")
            
            if self.memory_manager:
                history = self.memory_manager.get_context_window(history, max_turns=4)
            
            # 4b. Fetch User Profile for Personalization
            
            # 4c. Inject MCP Tools and run ReAct Loop or Direct Inference
            target_model = user_profile.get("preferred_model", MODEL_NAME) if user_profile else MODEL_NAME
            start_inference_time = time.time()

            # Dynamic inference provider resolution
            if provider:
                from app.infrastructure.inference.factory import InferenceProviderFactory
                inf_provider = InferenceProviderFactory.create_sync_provider(provider)
            else:
                inf_provider = self.inference_provider

            # Only run the agentic ReAct loop when specific operational tools are matched
            from app.domain.agent.react_harness import classify_intent
            matched_tools = classify_intent(sanitized_text)

            if self.mcp_client and matched_tools and decision != "rag":
                # Run the ReAct agentic loop with lean component passing
                from app.domain.agent.tool_registry import ToolRegistry
                from app.domain.agent.react_harness import ReactHarness
                from app.core.security.pii_pipeline import deanonymize_text

                registry = ToolRegistry(self.mcp_client)
                harness = ReactHarness(inf_provider, registry, self.gatekeeper)

                # Pass raw components — the harness assembles the prompt once
                raw_response_text, steps = await harness.execute(
                    user_query=sanitized_text,
                    system_prompt=system_prompt,
                    history=history or [],
                    rag_docs=results if decision == "rag" else [],
                    user_profile=user_profile,
                    source=source,
                    token_map=entities,
                    model_name=target_model
                )

                # Store raw response (which might contain tokens) in state DB
                SovereignStateManager.store_message(client_msg_id or "default", "user", sanitized_text)
                SovereignStateManager.store_message(client_msg_id or "default", "assistant", raw_response_text)

                # Restore PII on the response returned to the user
                response_text = deanonymize_text(raw_response_text, entities)
                latency_ms = (time.time() - start_inference_time) * 1000
                response_obj = None
            else:
                # Classic direct / RAG flow
                prompt = self.context_manager.build_final_prompt(
                    system_prompt=system_prompt,
                    history=history,
                    rag_docs=results if decision == "rag" else [],
                    user_query=sanitized_text,
                    user_profile=user_profile,
                    source=source
                )

                # Construct clean structured chat messages for chat/instruct models
                system_instruction = system_prompt
                if decision == "rag" and results:
                    rag_text = self.context_manager.trim_rag_context(results)
                    system_instruction += f"\n\n### CONOCIMIENTO RELEVANTE (RAG):\n{rag_text}\n\n### REGLAS DE EVIDENCIA:\nResponde únicamente con base en el conocimiento relevante."

                chat_messages = [{"role": "system", "content": system_instruction}]
                if history:
                    for m in history:
                        if isinstance(m, dict) and "role" in m and "content" in m:
                            chat_messages.append({"role": m["role"], "content": m["content"]})
                chat_messages.append({"role": "user", "content": sanitized_text})

                request = InferenceRequest(
                    model=target_model,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    messages=chat_messages,
                    options={"temperature": 0.7, "max_tokens": 150}
                )
                import asyncio
                response_obj = await asyncio.to_thread(inf_provider.generate, request)
                response_text = response_obj.text
                latency_ms = (time.time() - start_inference_time) * 1000

                SovereignStateManager.store_message(client_msg_id or "default", "user", sanitized_text)
                SovereignStateManager.store_message(client_msg_id or "default", "assistant", response_text)

            pii_masked = [k for k in entities.keys()] if isinstance(entities, dict) else []
            raw_payload = getattr(response_obj, "raw_payload", None) or {}
            zyrabit_metrics = raw_payload.get("zyrabit") or {}

            ttft_ms = zyrabit_metrics.get("ttft_ms")
            if ttft_ms is None and "prompt_eval_duration" in raw_payload:
                p_dur = raw_payload.get("prompt_eval_duration", 0) or 0
                if p_dur > 0:
                    ttft_ms = round(p_dur / 1_000_000, 2)

            tps = zyrabit_metrics.get("tps")
            if tps is None and "eval_count" in raw_payload and "eval_duration" in raw_payload:
                e_count = raw_payload.get("eval_count", 0) or 0
                e_dur = raw_payload.get("eval_duration", 0) or 0
                if e_count > 0 and e_dur > 0:
                    tps = round(e_count / (e_dur / 1_000_000_000), 2)
            if tps is None and latency_ms > 0 and response_text:
                # Estimate word/token count throughput if lower-level durations were not captured
                est_tokens = max(len(response_text.split()), 1)
                tps = round(est_tokens / (latency_ms / 1000.0), 2)
            if ttft_ms is None and latency_ms > 0:
                ttft_ms = round(latency_ms * 0.2, 2)

            execution_target = getattr(response_obj, "execution_target", None) or {
                "engine": zyrabit_metrics.get("source") or getattr(inf_provider, "provider_name", "local"),
                "device": "cpu_generic" if "docker" in zyrabit_metrics.get("mode", "") else "accelerated",
                "backend": zyrabit_metrics.get("mode", "standard"),
                "accelerated": zyrabit_metrics.get("mode") not in ("docker", "cpu"),
            }

            # Telemetry observations
            if self.telemetry:
                if ttft_ms is not None:
                    try:
                        self.telemetry.record_ttft(ttft_ms, model=target_model, device=execution_target.get("device", "cpu"))
                    except TypeError:
                        self.telemetry.record_ttft(ttft_ms)
                if tps is not None and hasattr(self.telemetry, "record_throughput"):
                    self.telemetry.record_throughput(tps, model=target_model, device=execution_target.get("device", "cpu"))
                p_tokens = zyrabit_metrics.get("prompt_tokens", 0) or raw_payload.get("prompt_eval_count", 0) or 0
                c_tokens = zyrabit_metrics.get("completion_tokens", 0) or raw_payload.get("eval_count", 0) or len(response_text.split())
                if hasattr(self.telemetry, "record_tokens"):
                    self.telemetry.record_tokens(p_tokens, c_tokens, model=target_model)
                if rag_retrieval_ms > 0 and hasattr(self.telemetry, "record_rag_search"):
                    self.telemetry.record_rag_search(rag_retrieval_ms, hits=len(sources))

            final_response = {
                "response": response_text,
                "metadata": {
                    "model": target_model,
                    "decision": decision,
                    "latency_ms": round(latency_ms, 2),
                    "rag_retrieval_ms": rag_retrieval_ms,
                    "tps": tps,
                    "ttft_ms": ttft_ms,
                    "engine": zyrabit_metrics.get("source") or getattr(inf_provider, "provider_name", "local"),
                    "mode": zyrabit_metrics.get("mode"),
                    "execution_target": execution_target,
                    "sources": sources,
                    "rag_hits": len(sources) if (decision == "rag" and sources) else 0,
                    "pii_detected": any(entities.values()),
                    "pii_masked": pii_masked,
                    "cached": False
                }
            }

            # 6. Cache
            if client_msg_id:
                self.cache.set(client_msg_id, final_response)

            return final_response

        except Exception as e:
            self.telemetry.log_security_audit(f"CRITICAL ERROR: {e}")
            return {"response": "Critical Error", "metadata": {"decision": "error"}}

    def mask_query(self, query: str) -> tuple[str, bool]:
        """
        Sanitizes PII in user query.
        Returns: (clean_text, pii_detected)
        """
        clean_text, entities = self.gatekeeper.mask_pii(query)
        self.telemetry.log_security_audit(clean_text)
        pii_detected = any(entities.values()) if isinstance(entities, dict) else bool(entities)
        return clean_text, pii_detected

    async def stream_response(
        self,
        clean_query: str,
        history: list,
        user_profile: dict,
    ):
        """
        Runs RAG retrieval, composes prompt, and streams tokens.
        Decoupled from HTTP delivery. Yields strings (tokens) first,
        and finally yields a dict with metadata (e.g. rag_hits).
        """
        if self.memory_manager:
            history = self.memory_manager.get_context_window(history, max_turns=4)

        # RAG retrieval
        context_docs = []
        if self.retriever_service:
            try:
                candidates = await self.retriever_service.search(clean_query)
                if candidates:
                    if self.reranker:
                        # Advanced RAG: Re-Rank candidates and filter
                        ranked_docs = self.reranker.rerank(clean_query, candidates)
                        context_docs = [doc for doc, score in ranked_docs if score >= 0.6][:3]
                    else:
                        context_docs = candidates[:3]
            except Exception as e:
                self.telemetry.log_security_audit(f"RAG stream search failed: {e}")

        # Build prompt
        user_profile = user_profile or {}
        system_prompt = (user_profile.get("system_prompt") or "").strip() or "You are Zyra, a helpful sovereign assistant."
        
        # Inject MCP Tools for stream
        if self.mcp_client:
            try:
                tools = await self.mcp_client.get_tools()
                if tools:
                    tools_desc = "\\n".join([f"- {t['name']}: {t['description']}" for t in tools])
                    system_prompt += f"\\n\\nYou have access to the following tools:\\n{tools_desc}\\nIf you need to use a tool, reply ONLY with a JSON block: ```json\\n{{\"tool\": \"tool_name\", \"arguments\": {{}}}}```"
            except Exception as e:
                self.telemetry.log_security_audit(f"Failed to fetch MCP tools for stream: {e}")
                
        prompt = self.context_manager.build_final_prompt(
            system_prompt=system_prompt,
            history=history,
            rag_docs=context_docs,
            user_query=clean_query,
            user_profile=user_profile,
            source="AG-UI"
        )

        # Select model based on profile preference
        target_model = user_profile.get("preferred_model", MODEL_NAME) if user_profile else MODEL_NAME

        # Stream tokens
        if not self.streaming_provider:
            raise RuntimeError("Streaming provider not configured for ChatUseCase")
        
        start_time = time.time()
        first_chunk_received = False
        
        request = InferenceRequest(
            model=target_model,
            prompt=prompt,
            system_prompt=system_prompt,
            stream=True
        )
        
        async for token in self.streaming_provider.stream_generate(request):
            if not first_chunk_received:
                duration_ms = (time.time() - start_time) * 1000
                self.telemetry.record_ttft(duration_ms)
                first_chunk_received = True
            yield token

        # Yield metadata at the end of the generator
        yield {"rag_hits": len(context_docs)}

    def save_interaction(self, thread_id: str, clean_query: str, response_text: str) -> None:
        """Sovereign DB persistence - completely decoupled from HTTP transport."""
        SovereignStateManager.store_message(thread_id, "user", clean_query)
        SovereignStateManager.store_message(thread_id, "assistant", response_text)
