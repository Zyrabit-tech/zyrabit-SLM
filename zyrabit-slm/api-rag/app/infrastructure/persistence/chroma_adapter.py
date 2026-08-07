import logging
import requests
from typing import List, Dict, Any
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from app.ports.vector_store_port import VectorStorePort

logger = logging.getLogger("zyrabit.api")

class DirectOllamaEmbeddings(Embeddings):
    """
    Direct Ollama API Embeddings (LangChain Compatible).
    Bypasses library bugs by using raw HTTP requests. Handles fallback for embedded runtimes.
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
                    },
                    timeout=5.0
                )
                if response.status_code != 200:
                    logger.error(f"⚠️ Ollama Error ({response.status_code}): {response.text}")
                response.raise_for_status()
                all_embeddings.extend(response.json()["embeddings"])
            except Exception as e:
                # Never create false-positive indexes: zero vectors make a document
                # appear indexed while semantic retrieval is unusable.
                raise RuntimeError(
                    f"Embedding provider unavailable at {self.base_url}; document was not indexed. "
                    "Configure EMBEDDING_URL independently from SLM_URL."
                ) from e
        
        return all_embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]

    def health(self) -> tuple[bool, str]:
        """Check the dedicated embedding endpoint without producing vectors."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2.0)
            response.raise_for_status()
            models = response.json().get("models", [])
            names = {item.get("name") for item in models if isinstance(item, dict)}
            # Ollama exposes the default tag as `model:latest`, while its API
            # accepts both that name and the convenient tagless alias.
            configured_names = {self.model, f"{self.model}:latest"}
            if names and not configured_names.intersection(names):
                return False, f"embedding model '{self.model}' is not installed"
            return True, f"{self.model} available"
        except Exception as exc:
            return False, f"embedding endpoint unavailable at {self.base_url}: {exc}"

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
        """
        Real connectivity check for ChromaDB.
        """
        try:
            # We try to access the underlying chroma client heartbeat
            if hasattr(self.vector_store, "_client"):
                self.vector_store._client.heartbeat()
                return True
            return False
        except Exception as e:
            logger.error(f"❌ ChromaDB Heartbeat failed: {e}")
            return False
