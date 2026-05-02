import chromadb
import logging
from typing import List, Dict, Any, Optional
from app.ports.vector_store_port import VectorStorePort

logger = logging.getLogger("uvicorn.error")

class SearchResult:
    """Standardized search result document."""
    def __init__(self, content: str, metadata: Dict[str, Any]):
        self.page_content = content
        self.metadata = metadata

class LangchainEmbeddingAdapter:
    """Wrapper to make LangChain embeddings compatible with native ChromaDB."""
    def __init__(self, langchain_embeddings: Any):
        self.langchain_embeddings = langchain_embeddings

    def __call__(self, input: List[str]) -> List[List[float]]:
        # Chroma passes a list of strings.
        try:
            if not input:
                return []
            
            # For a single query (standard RAG search)
            if len(input) == 1:
                return [self.langchain_embeddings.embed_query(input[0])]
            
            # For multiple documents (ingestion)
            return self.langchain_embeddings.embed_documents(input)
        except Exception as e:
            logger.error(f"❌ Embedding call failed: {e}")
            raise

    def embed_query(self, input: str) -> List[float]:
        return self.langchain_embeddings.embed_query(input)

    def name(self) -> str:
        return self.langchain_embeddings.__class__.__name__

class ChromaAdapter(VectorStorePort):
    def __init__(self, host: str, port: int, collection_name: str, embedding_function: Any):
        try:
            self.client = chromadb.HttpClient(host=host, port=port)
            
            # Wrap if it's a LangChain embedding object
            if hasattr(embedding_function, "embed_documents") and not hasattr(embedding_function, "name"):
                embedding_function = LangchainEmbeddingAdapter(embedding_function)

            self.collection = self.client.get_or_create_collection(
                name=collection_name, 
                embedding_function=embedding_function
            )
            logger.info(f"✅ Connected to ChromaDB collection: {collection_name}")
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
            # Chroma returns { 'documents': [[...]], 'metadatas': [[...]], ... }
            if results.get("documents") and len(results["documents"]) > 0:
                for i in range(len(results["documents"][0])):
                    content = results["documents"][0][i]
                    # Safely handle metadatas
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
