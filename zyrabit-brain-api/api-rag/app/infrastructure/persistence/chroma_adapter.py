import chromadb
from typing import List, Dict, Any, Optional
from ...ports.vector_store_port import VectorStorePort
from urllib.parse import urlparse

class ChromaAdapter(VectorStorePort):
    def __init__(self, host: str, port: int, collection_name: str, embedding_function: Any):
        self.client = chromadb.HttpClient(host=host, port=port)
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
