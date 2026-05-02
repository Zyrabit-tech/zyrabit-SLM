import os
import uuid
import logging
from typing import List, Dict, Any
from app.infrastructure.shared.config import SLM_URL, RAG_COLLECTION
from app.infrastructure.shared.state_tracker import IngestionTracker

logger = logging.getLogger("uvicorn.error")

class IngestUseCase:
    """
    Handles end-to-end document ingestion: Loading -> Chunking -> Vectorizing.
    """
    def __init__(self, vector_store):
        self.vector_store = vector_store

    async def execute(self, file_path: str):
        """
        Executes the full ingestion pipeline for a file.
        """
        doc_id = str(uuid.uuid4())
        filename = os.path.basename(file_path)
        
        # 1. Register PENDING state
        IngestionTracker.register_ingest(doc_id, filename)
        
        try:
            # 2. Load and Split
            chunks, metadatas = self._load_and_split(file_path)
            
            # 3. Ingest into Vector Store
            for m in metadatas:
                m["doc_id"] = doc_id
                m["source"] = filename
                
            ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
            self.vector_store.add_texts(chunks, metadatas=metadatas, ids=ids)
            
            # 4. Mark as COMPLETED
            IngestionTracker.complete_ingest(doc_id)
            logger.info(f"✅ Ingestion successful: {filename} ({len(chunks)} chunks)")
            return {"status": "success", "doc_id": doc_id, "chunks": len(chunks)}
            
        except Exception as e:
            logger.error(f"❌ Ingestion failed for {filename}: {e}")
            # The Garbage Collector will clean this up on next startup
            return {"status": "error", "message": str(e), "doc_id": doc_id}

    def _load_and_split(self, file_path: str):
        """
        Internal logic for parsing files and creating chunks.
        Uses LangChain loaders and splitters.
        """
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        if file_path.lower().endswith(".pdf"):
            from langchain_community.document_loaders import PyMuPDFLoader
            loader = PyMuPDFLoader(file_path)
        elif file_path.lower().endswith(".md"):
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(file_path)
        else:
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(file_path)
            
        docs = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        split_docs = text_splitter.split_documents(docs)
        
        chunks = [d.page_content for d in split_docs]
        metadatas = [d.metadata for d in split_docs]
        
        return chunks, metadatas
