import logging
from typing import List, Optional
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_chroma import Chroma
from langchain_core.documents import Document

logger = logging.getLogger("zyrabit.api")

class HybridRetrieverService:
    """
    Orchestrates Hybrid Search (Vector + BM25) for High Precision.
    """
    
    def __init__(self, vector_store: Chroma):
        self.vector_store = vector_store
        self.bm25_retriever: Optional[BM25Retriever] = None
        self.ensemble_retriever: Optional[EnsembleRetriever] = None

    def update_bm25_index(self, documents: List[Document]):
        """
        Updates the BM25 index with new documents for exact keyword matching.
        """
        logger.info(f"📈 Updating BM25 index with {len(documents)} documents...")
        self.bm25_retriever = BM25Retriever.from_documents(documents)
        
        # Configure Ensemble: 70% Vector / 30% BM25
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[
                self.vector_store.as_retriever(search_kwargs={"k": 3}),
                self.bm25_retriever
            ],
            weights=[0.7, 0.3]
        )
        logger.info("✅ Hybrid Ensemble Retriever ready.")

    async def search(self, query: str, domain: Optional[str] = None) -> List[Document]:
        """
        Executes hybrid search with FTS5 Fast-Path and Vector Fallback.
        """
        from app.infrastructure.shared.state_tracker import SovereignStateManager
        
        logger.info(f"⚡ FTS5 Fast-Path Search for: '{query}'")
        fts_results = SovereignStateManager.search_fts(query)
        
        if fts_results:
            logger.info(f"🚀 FTS5 Hit! Found {len(fts_results)} results instantly.")
            return [Document(page_content=r["snippet"], metadata={"source": r["file_path"], "type": "fts5"}) for r in fts_results]

        if not self.ensemble_retriever:
            logger.warning("⚠️ Ensemble Retriever not initialized. Falling back to Vector-only.")
            return self.vector_store.similarity_search(query, k=3)
            
        logger.info(f"🔎 Falling back to Hybrid Ensemble (Vector+BM25) for: '{query}'")
        results = self.ensemble_retriever.invoke(query)
        return results

