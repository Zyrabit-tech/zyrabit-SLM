import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
from app.domain.ports.telemetry_port import TelemetryPort
from app.infrastructure.shared.config import MODEL_NAME
from app.infrastructure.shared.state_tracker import SovereignStateManager
from app.domain.services.context_manager import ContextManager
from app.ports.inference_port import InferenceRequest

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

    async def execute(self, text: str, client_msg_id: Optional[str] = None, history: Optional[list] = None, source: str = "WEB") -> Dict[str, Any]:
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
            if decision == "rag":
                if not self.retriever_service:
                    logger.warning("⚠️ Hybrid Retriever not initialized. Falling back to direct.")
                    decision = "direct (no-retriever)"
                else:
                    try:
                        results = await self.retriever_service.search(sanitized_text)
                        if results:
                            if self.reranker:
                                # Advanced RAG: Re-Rank candidates and filter
                                ranked_docs = self.reranker.rerank(sanitized_text, results)
                                results = [doc for doc, score in ranked_docs if score >= 0.6][:3]
                            else:
                                results = results[:3]
                                
                            if results:
                                sources = list(set([r.metadata.get("source", "unknown") for r in results]))
                    except Exception as e:
                        self.telemetry.log_security_audit(f"RAG search failed: {e}")
                        decision = "direct (fallback)"

            # 4. Inference
            # Load system prompt from user profile, fallback to default
            user_profile = SovereignStateManager.get_user_profile()
            system_prompt = (user_profile.get("system_prompt") or "").strip() or "You are Zyra, a helpful sovereign assistant."

            # 4. Memory Recovery
            if history is None:
                history = SovereignStateManager.get_history(client_msg_id or "default")
            
            if self.memory_manager:
                history = self.memory_manager.get_context_window(history, max_turns=4)
            
            # 4b. Fetch User Profile for Personalization
            
            # 4c. Inject MCP Tools into system prompt
            if self.mcp_client:
                try:
                    tools = await self.mcp_client.get_tools()
                    if tools:
                        tools_desc = "\\n".join([f"- {t['name']}: {t['description']} (Schema: {t['inputSchema']})" for t in tools])
                        system_prompt += f"\\n\\nYou have access to the following tools:\\n{tools_desc}\\nIf you need to use a tool, reply ONLY with a JSON block: ```json\\n{{\"tool\": \"tool_name\", \"arguments\": {{}}}}```"
                except Exception as e:
                    self.telemetry.log_security_audit(f"Failed to fetch MCP tools: {e}")

            # 5. Build Final Prompt via ContextManager
            prompt = self.context_manager.build_final_prompt(
                system_prompt=system_prompt,
                history=history,
                rag_docs=results if decision == "rag" else [],
                user_query=sanitized_text,
                user_profile=user_profile,
                source=source
            )



            # [NEW] Model Switching based on Persona/Profile Preference
            target_model = user_profile.get("preferred_model", MODEL_NAME) if user_profile else MODEL_NAME

            request = InferenceRequest(
                model=target_model, 
                prompt=prompt,
                system_prompt=system_prompt
            )
            import asyncio
            response_obj = await asyncio.to_thread(self.inference_provider.generate, request)

            
            # 6. Persist interaction to Sovereign State
            SovereignStateManager.store_message(client_msg_id or "default", "user", sanitized_text)
            SovereignStateManager.store_message(client_msg_id or "default", "assistant", response_obj.text)

            pii_masked = [k for k in entities.keys()] if isinstance(entities, dict) else []
            latency_ms = response_obj.latency_seconds * 1000
            final_response = {
                "response": response_obj.text,
                "metadata": {
                    "decision": decision,
                    "latency_ms": round(latency_ms, 2),
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

