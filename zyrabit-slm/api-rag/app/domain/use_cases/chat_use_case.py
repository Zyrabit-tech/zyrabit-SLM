import logging
from typing import Optional, Dict, Any
from app.infrastructure.shared.config import MODEL_NAME
from app.infrastructure.shared.metrics import TOKEN_USAGE_TOTAL, TOKEN_LATENCY_MS, SECURITY_HITS_TOTAL, RAG_HITS_TOTAL
from app.ports.inference_port import InferenceRequest

logger = logging.getLogger("zyrabit.api")

class ChatUseCase:
    """
    V5.0 Brain: Orchestrates Security, Hybrid RAG, and Inference.
    """
    def __init__(self, inference_provider, retriever_service, gatekeeper, cache):
        self.inference_provider = inference_provider
        self.retriever_service = retriever_service
        self.gatekeeper = gatekeeper
        self.cache = cache

    async def execute(self, text: str, client_msg_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            # 0. Idempotency Check
            if client_msg_id:
                cached_res = self.cache.get(client_msg_id)
                if cached_res:
                    cached_res["metadata"]["cached"] = True
                    return cached_res

            # 1. Security Check (PII Masking)
            sanitized_text, entities = self.gatekeeper.mask_pii(text)
            
            if any(entities.values()):
                found = [k for k, v in entities.items() if v]
                logger.info(f"🛡️ PII Detected! Masked entities: {found}")
                logger.debug(f"Original: {text}")
                logger.info(f"Sanitized: {sanitized_text}")
            
            # 2. Routing Decision
            decision = self.gatekeeper.get_routing_decision(sanitized_text)
            
            if decision == "reject":
                return {
                    "response": "I'm sorry, that query is out of scope.",
                    "metadata": {"decision": "rejected", "cached": False}
                }

            # 3. Hybrid Context Retrieval (RAG)
            context = ""
            sources = []
            if decision == "rag":
                if not self.retriever_service:
                    logger.warning("⚠️ Hybrid Retriever not initialized. Falling back to direct.")
                    decision = "direct (no-retriever)"
                else:
                    try:
                        results = await self.retriever_service.search(sanitized_text)
                        if results:
                            context = "\n".join([r.page_content for r in results])
                            sources = list(set([r.metadata.get("source", "unknown") for r in results]))
                    except Exception as e:
                        logger.error(f"⚠️ Hybrid Search failed: {e}")
                        decision = "direct (fallback)"

            # 4. Inference
            system_prompt_path = "app/infrastructure/shared/prompts/zyra_system.md"
            try:
                with open(system_prompt_path, "r", encoding="utf-8") as f:
                    system_prompt = f.read()
            except Exception as e:
                logger.warning(f"⚠️ Could not load system prompt from {system_prompt_path}: {e}")
                system_prompt = "You are Zyra, a helpful assistant."
            
            prompt = sanitized_text
            if context:
                prompt = f"Context:\n{context}\n\nQuestion: {sanitized_text}\n\nAnswer based ONLY on the context provided:"

            request = InferenceRequest(
                model=MODEL_NAME, 
                prompt=prompt,
                system_prompt=system_prompt
            )
            response_obj = self.inference_provider.generate(request)
            
            latency_ms = response_obj.latency_seconds * 1000
            final_response = {
                "response": response_obj.text,
                "metadata": {
                    "decision": decision,
                    "latency_ms": round(latency_ms, 2),
                    "sources": sources,
                    "pii_detected": any(entities.values()),
                    "cached": False
                }
            }
            
            # 5. Cache
            if client_msg_id:
                self.cache.set(client_msg_id, final_response)

            return final_response

        except Exception as e:
            logger.exception(f"❌ Critical error in ChatUseCase: {e}")
            return {"response": "Critical Error", "metadata": {"decision": "error"}}
