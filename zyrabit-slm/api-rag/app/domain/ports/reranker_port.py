from abc import ABC, abstractmethod
from typing import List, Tuple
from langchain_core.documents import Document

class ReRankerPort(ABC):
    """
    Contract for semantic chunk re-ranking.
    """
    @abstractmethod
    def rerank(self, query: str, documents: List[Document]) -> List[Tuple[Document, float]]:
        """
        Ranks documents against the user query.
        Returns: A list of tuples (Document, relevance_score) where score is 0.0 to 1.0.
        """
        pass
