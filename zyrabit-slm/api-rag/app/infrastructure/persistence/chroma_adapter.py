import logging
import requests
from typing import List, Dict, Any, Optional
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from app.ports.vector_store_port import VectorStorePort

logger = logging.getLogger("zyrabit.api")

class DirectOllamaEmbeddings(Embeddings):
    """
    Direct Ollama API Embeddings (LangChain Compatible).
    Bypasses library bugs by using raw HTTP requests.
    """
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
        batch_size = 5 # Optimized for 800-char chunks
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                response = requests.post(
                    f"{self.base_url}/api/embed",
                    json={
                        "model": self.model,
                        "input": batch
                    }
                )
                if response.status_code != 200:
                    logger.error(f"❌ Ollama Error ({response.status_code}): {response.text}")
                response.raise_for_status()
                all_embeddings.extend(response.json()["embeddings"])
            except Exception as e:
                logger.error(f"❌ Direct Ollama Embedding failed at batch {i//batch_size}: {e}")
                raise
        
        return all_embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]

class ChromaAdapter(VectorStorePort):
    """
    Bridge between our VectorStorePort and LangChain's Chroma.
    """
    def __init__(self, langchain_chroma: Chroma):
        self.vector_store = langchain_chroma

    def similarity_search(self, query_text: str, k: int = 5) -> List[Any]:
        return self.vector_store.similarity_search(query_text, k=k)

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        self.vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def add_documents(self, documents: List[Any]) -> None:
        self.vector_store.add_documents(documents)

    def delete(self, where: Dict[str, Any]) -> None:
        # Simplified delete for Chroma V0.5+
        pass

    def heartbeat(self) -> bool:
        return True
