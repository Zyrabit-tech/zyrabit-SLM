from typing import List, Dict, Any
from abc import ABC, abstractmethod

class VectorStorePort(ABC):
    @abstractmethod
    def query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """Query the vector store for relevant documents."""
        pass

    @abstractmethod
    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        """Add documents to the vector store."""
        pass

    @abstractmethod
    def heartbeat(self) -> bool:
        """Check if the vector store is reachable."""
        pass
