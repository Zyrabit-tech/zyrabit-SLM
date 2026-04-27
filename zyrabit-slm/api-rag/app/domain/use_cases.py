from typing import Tuple, Dict, Any, List
from ..ports.inference_port import InferenceProviderPort, InferenceRequest
from ..ports.vector_store_port import VectorStorePort
import logging

logger = logging.getLogger("uvicorn.error")

from app.core.telemetry_metrics import zyrabit_token_usage_total, zyrabit_token_latency_ms_per_token

class ChatUseCase:
    def __init__(self, inference_provider: InferenceProviderPort, vector_store: VectorStorePort, system_prompt: str):
        self.inference_provider = inference_provider
        self.vector_store = vector_store
        self.system_prompt = system_prompt

    def execute_rag(self, query_text: str, model_name: str) -> Tuple[str, int, float, List[str]]:
        """Retrieve from vector store and generate response with citations."""
        logger.info("Executing RAG Use Case for query: %s", query_text[:50])
        
        # 1. Retrieval
        search_results = self.vector_store.query(query_text)
        docs = search_results.get("documents", [[]])[0]
        metas = search_results.get("metadatas", [[]])[0]
        rag_hits = len(docs)
        
        # Extract unique sources
        sources = list(set([m.get("source", "Unknown") for m in metas]))
        
        context = "\n\n".join(docs) if docs else "No relevant context found."
        
        # 2. Augmentation
        augmented_prompt = f"{self.system_prompt}\n\nContext from knowledge base:\n{context}\n\nUser: {query_text}\nAssistant:"
        
        # 3. Generation
        result = self.inference_provider.generate(
            InferenceRequest(model=model_name, prompt=augmented_prompt)
        )
        
        # Increment metrics (heuristic: 1 token ~= 4 chars)
        tokens = max(1, len(result.text) // 4)
        zyrabit_token_usage_total.labels(model=model_name, provider=self.inference_provider.provider_name).inc(tokens)
        zyrabit_token_latency_ms_per_token.labels(model=model_name, provider=self.inference_provider.provider_name).observe((result.latency_seconds * 1000) / tokens)
        
        return result.text, rag_hits, result.latency_seconds, sources

    def execute_direct_chat(self, query_text: str, model_name: str) -> Tuple[str, float]:
        """Generate response without RAG."""
        logger.info("Executing Direct Chat Use Case")
        full_prompt = f"{self.system_prompt}\n\nUser: {query_text}\nAssistant:"
        result = self.inference_provider.generate(
            InferenceRequest(model=model_name, prompt=full_prompt)
        )
        # Increment metrics
        tokens = max(1, len(result.text) // 4)
        zyrabit_token_usage_total.labels(model=model_name, provider=self.inference_provider.provider_name).inc(tokens)
        zyrabit_token_latency_ms_per_token.labels(model=model_name, provider=self.inference_provider.provider_name).observe((result.latency_seconds * 1000) / tokens)
        
        return result.text, result.latency_seconds

class IngestUseCase:
    def __init__(self, vector_store: VectorStorePort):
        self.vector_store = vector_store

    def ingest_text_chunks(self, chunks: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        self.vector_store.add_documents(chunks, metadatas, ids)
