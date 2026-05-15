import os
import uuid
import logging
from app.infrastructure.shared.state_tracker import SovereignStateManager
from app.infrastructure.shared.validators.ingestion_validator import IngestionValidator
from app.infrastructure.persistence.pdf_processor import PDFProcessor
from app.domain.services.document_chunker import DocumentChunker

logger = logging.getLogger("zyrabit.api")

class IngestUseCase:
    """
    V5.0 High Precision Ingestion Pipeline.
    """
    def __init__(self, vector_store, retriever_service=None):
        self.vector_store = vector_store
        self.retriever_service = retriever_service
        self.chunker = DocumentChunker()

    async def execute(self, file_path: str, domain: str = "general"):
        """
        Executes the high-precision ingestion pipeline.
        """
        filename = os.path.basename(file_path)
        
        # 1. Validation (Fail-Fast)
        error = IngestionValidator.validate(file_path)
        if error:
            logger.error(f"❌ Validation failed for {filename}: {error}")
            return {"status": "error", "message": error}
            
        # 1b. Hashing Check (Avoid Redundant Work)
        if not SovereignStateManager.needs_reindexing(file_path):
            logger.info(f"⏩ Skipping {filename} - already indexed and unchanged.")
            return {"status": "skipped", "message": "unchanged"}

        doc_id = str(uuid.uuid4())
        
        try:
            # 2. Extract (Markdown Paradigm)
            documents = PDFProcessor.to_markdown_documents(file_path)
            
            # 3. Structural Chunking
            chunks = self.chunker.split(documents, domain=domain)
            
            # 4. Ingest into Vector Store
            # In V5.0 we use the LangChain vector store directly
            self.vector_store.add_documents(chunks)
            
            if self.retriever_service:
                self.retriever_service.update_bm25_index(chunks)
            
            SovereignStateManager.update_vault_index(file_path, len(chunks))
            logger.info(f"✅ High-Precision Ingestion successful: {filename}")
            return {"status": "success", "doc_id": doc_id, "chunks": len(chunks)}
            
        except Exception as e:
            logger.error(f"❌ Ingestion failed for {filename}: {e}")
            return {"status": "error", "message": str(e), "doc_id": doc_id}
