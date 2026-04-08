import chromadb
from typing import List, Dict, Any, Optional
from ...ports.vector_store_port import VectorStorePort
from urllib.parse import urlparse

class LangchainEmbeddingAdapter:
    """Wrapper to make LangChain embeddings compatible with native ChromaDB."""
    def __init__(self, langchain_embeddings: Any):
        self.langchain_embeddings = langchain_embeddings

    def __call__(self, input: List[str]) -> List[List[float]]:
        return self.langchain_embeddings.embed_documents(input)

    def embed_query(self, input: str) -> List[float]:
        """Specific method required by some ChromaDB versions/paths."""
        return self.langchain_embeddings.embed_query(input)

    def name(self) -> str:
        return self.langchain_embeddings.__class__.__name__

class ChromaAdapter(VectorStorePort):
    def __init__(self, host: str, port: int, collection_name: str, embedding_function: Any):
        self.client = chromadb.HttpClient(host=host, port=port)
        
        # Wrap if it's a LangChain embedding object (has embed_documents)
        if hasattr(embedding_function, "embed_documents") and not hasattr(embedding_function, "name"):
            embedding_function = LangchainEmbeddingAdapter(embedding_function)

        self.collection = self.client.get_or_create_collection(
            name=collection_name, 
            embedding_function=embedding_function
        )

    def query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def heartbeat(self) -> bool:
        try:
            self.client.heartbeat()
            return True
        except Exception:
            return False
