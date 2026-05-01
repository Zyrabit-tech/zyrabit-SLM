from abc import ABC, abstractmethod
from typing import List, Dict, Any

class VectorStorePort(ABC):
    """
    Interface for vector database operations.
    Follows Hexagonal Architecture principles.
    """
    
    @abstractmethod
    def similarity_search(self, query_text: str, k: int = 5) -> List[Any]:
        """Search for most similar documents."""
        pass

    @abstractmethod
    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        """Add text documents to the vector store."""
        pass

    @abstractmethod
    def delete(self, where: Dict[str, Any]) -> None:
        """Delete documents from the vector store."""
        pass

    @abstractmethod
    def heartbeat(self) -> bool:
        """Check connection health."""
        pass
