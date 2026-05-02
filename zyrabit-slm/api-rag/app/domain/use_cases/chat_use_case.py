import time
import logging
from typing import Optional, Dict, Any
from app.infrastructure.shared.config import MODEL_NAME
from app.infrastructure.shared.metrics import TOKEN_USAGE_TOTAL, TOKEN_LATENCY_MS, SECURITY_HITS_TOTAL, RAG_HITS_TOTAL
from app.ports.inference_port import InferenceRequest

logger = logging.getLogger("uvicorn.error")

class ChatUseCase:
    """
    The brain of the conversation. Orchestrates security, RAG, and Inference.
    """
    def __init__(self, inference_provider, vector_store, gatekeeper, cache):
        self.inference_provider = inference_provider
        self.vector_store = vector_store
        self.gatekeeper = gatekeeper
        self.cache = cache

    async def execute(self, text: str, client_msg_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            # 0. Idempotency Check
            if client_msg_id:
                cached_res = self.cache.get(client_msg_id)
                if cached_res:
                    return cached_res

            start_time = time.time()
            
            # 1. PII Masking
            sanitized_text, entities = self.gatekeeper.mask_pii(text)
            if any(entities.values()):
                for entity_type, found in entities.items():
                    if found:
                        SECURITY_HITS_TOTAL.labels(entity_type=entity_type, action="masked").inc(len(found))
            
            # 2. Routing Decision
            decision = self.gatekeeper.get_routing_decision(sanitized_text)
            
            if decision == "reject":
                SECURITY_HITS_TOTAL.labels(entity_type="scope", action="rejected").inc()
                return {
                    "response": "I'm sorry, that query is out of scope. I focus on Zyrabit SLM and infrastructure.",
                    "metadata": {"decision": "rejected", "cached": False}
                }

            # 3. Context Retrieval (RAG)
            context = ""
            sources = []
            if decision == "rag":
                RAG_HITS_TOTAL.labels(collection="zyrabit_knowledge").inc()
                try:
                    results = self.vector_store.similarity_search(sanitized_text, k=3)
                    if results:
                        context = "\n".join([r.page_content for r in results])
                        sources = list(set([r.metadata.get("source", "unknown") for r in results]))
                except Exception as e:
                    logger.error(f"⚠️ RAG Retrieval failed: {e}")
                    # Fallback to direct inference if RAG fails
                    decision = "direct (fallback)"

            # 4. Prompt Engineering
            prompt = sanitized_text
            if context:
                prompt = f"Context: {context}\n\nQuestion: {sanitized_text}\n\nAnswer based ONLY on context:"

            # 5. Inference
            request = InferenceRequest(
                model=MODEL_NAME,
                prompt=prompt
            )
            
            response_obj = self.inference_provider.generate(request)
            response_text = response_obj.text
            latency_ms = response_obj.latency_seconds * 1000
            
            # Metrics
            TOKEN_LATENCY_MS.labels(model=MODEL_NAME).observe(latency_ms)
            tokens_generated = response_obj.raw_payload.get("eval_count", 0)
            TOKEN_USAGE_TOTAL.labels(model=MODEL_NAME, direction="output").inc(tokens_generated)

            final_response = {
                "response": response_text,
                "metadata": {
                    "decision": decision,
                    "latency_ms": round(latency_ms, 2),
                    "sources": sources,
                    "pii_detected": any(entities.values()),
                    "cached": False
                }
            }
            
            # 6. Store in Cache
            if client_msg_id:
                cache_entry = final_response.copy()
                cache_entry["metadata"] = final_response["metadata"].copy()
                cache_entry["metadata"]["cached"] = True
                self.cache.set(client_msg_id, cache_entry)

            return final_response

        except Exception as e:
            logger.exception(f"❌ Critical error in ChatUseCase: {e}")
            return {
                "response": f"I encountered a critical error: {str(e)}",
                "metadata": {"decision": "error", "cached": False}
            }
