import chromadb
import logging
import requests
from typing import List, Dict, Any, Optional
from app.ports.vector_store_port import VectorStorePort
from app.infrastructure.shared.config import SLM_URL, EMBEDDING_MODEL

logger = logging.getLogger("zyrabit.api")

class SearchResult:
    """Standardized search result document."""
    def __init__(self, content: str, metadata: Dict[str, Any]):
        self.page_content = content
        self.metadata = metadata

class DirectOllamaEmbeddingFunction:
    """
    Bypasses buggy LangChain validation by calling Ollama API directly.
    """
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def __call__(self, input: List[str]) -> List[List[float]]:
        try:
            response = requests.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": input
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]
        except Exception as e:
            logger.error(f"❌ Direct Ollama Embedding failed: {e}")
            raise

class ChromaAdapter(VectorStorePort):
    def __init__(self, host: str, port: int, collection_name: str, embedding_function: Any = None):
        try:
            self.client = chromadb.HttpClient(host=host, port=port)
            
            # Use our direct, reliable embedding function
            reliable_ef = DirectOllamaEmbeddingFunction(
                model=EMBEDDING_MODEL,
                base_url=SLM_URL
            )

            self.collection = self.client.get_or_create_collection(
                name=collection_name, 
                embedding_function=reliable_ef
            )
            logger.info(f"✅ Connected to ChromaDB with Direct Ollama Embeddings")
        except Exception as e:
            logger.error(f"❌ Failed to initialize ChromaAdapter: {e}")
            raise

    def similarity_search(self, query_text: str, k: int = 5) -> List[Any]:
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=k
            )
            
            documents = []
            if results.get("documents") and len(results["documents"]) > 0:
                for i in range(len(results["documents"][0])):
                    content = results["documents"][0][i]
                    meta = {}
                    if results.get("metadatas") and len(results["metadatas"]) > 0:
                        meta = results["metadatas"][0][i] or {}
                    
                    documents.append(SearchResult(content=content, metadata=meta))
            
            return documents
        except Exception as e:
            logger.error(f"❌ Similarity search failed in ChromaAdapter: {e}")
            raise

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        try:
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
        except Exception as e:
            logger.error(f"❌ Failed to add texts to Chroma: {e}")
            raise

    def delete(self, where: Dict[str, Any]) -> None:
        self.collection.delete(where=where)

    def heartbeat(self) -> bool:
        try:
            self.client.heartbeat()
            return True
        except Exception:
            return False
