import os
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

    async def execute(self, text: str, client_msg_id: Optional[str] = None, history: Optional[list] = None) -> Dict[str, Any]:
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
            # Attempt to find system prompt in multiple locations (Local vs Docker)
            possible_paths = [
                "app/infrastructure/shared/prompts/zyra_system.md",
                "zyrabit-slm/api-rag/app/infrastructure/shared/prompts/zyra_system.md",
                "/app/app/infrastructure/shared/prompts/zyra_system.md"
            ]
            system_prompt = "You are Zyra, a helpful sovereign assistant."
            for p in possible_paths:
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            system_prompt = f.read()
                        break
                    except: continue

            # 4. Memory Integration (Last 5 turns)
            memory_context = ""
            if history:
                # Take last 10 messages (5 turns)
                recent = history[-10:]
                memory_context = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent])

            # Construct High-Precision Prompt
            if context:
                prompt = f"""### CONOCIMIENTO DEL VAULT (FRAGMENTOS):
{context}

### HISTORIAL RECIENTE:
{memory_context if memory_context else "No hay historial previo."}

### CONSULTA DEL USUARIO:
{sanitized_text}

### INSTRUCCIÓN DE RESPUESTA:
Utiliza el conocimiento del Vault y el historial para responder. Si es un resumen, básate en el Vault."""
            else:
                prompt = f"""### HISTORIAL RECIENTE:
{memory_context if memory_context else "No hay historial previo."}

### CONSULTA:
{sanitized_text}

### IDENTIDAD: Eres Zyra de Zyrabit. Responde de forma inteligente y soberana."""

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
                    "rag_hits": len(sources) if context else 0,
                    "pii_detected": any(entities.values()),
                    "cached": False
                }
            }
            
            # 5. Metrics Recording
            TOKEN_LATENCY_MS.labels(model=MODEL_NAME).observe(latency_ms)
            # Estimate tokens as words (approximate for SLM visibility)
            token_count = len(response_obj.text.split())
            TOKEN_USAGE_TOTAL.labels(model=MODEL_NAME, direction="output").inc(token_count)
            if decision == "rag" and sources:
                RAG_HITS_TOTAL.labels(collection="default").inc()

            # 6. Cache
            if client_msg_id:
                self.cache.set(client_msg_id, final_response)

            return final_response

        except Exception as e:
            logger.exception(f"❌ Critical error in ChatUseCase: {e}")
            return {"response": "Critical Error", "metadata": {"decision": "error"}}
