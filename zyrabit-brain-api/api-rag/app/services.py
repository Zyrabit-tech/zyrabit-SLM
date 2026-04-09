import os
import logging
from typing import Dict, Any, List, Tuple
from .infrastructure.persistence.chroma_adapter import ChromaAdapter
from .infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter
from .domain.use_cases import IngestUseCase, ChatUseCase
from .domain.services.gatekeeper import Gatekeeper
from .ports.inference_port import InferenceRequest
from urllib.parse import urlparse
from langchain_ollama import OllamaEmbeddings

logger = logging.getLogger("uvicorn.error")

# --- Configuration ---
SLM_URL = os.getenv("SLM_URL", "http://slm-engine:11434")
DB_URL = os.getenv("DB_URL", "http://vector-db:8000")
COLLECTION_NAME = os.getenv("RAG_COLLECTION", "zyrabit_knowledge")

def load_system_prompt() -> str:
    """Loads the system prompt from the local file."""
    prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "You are a helpful Zyrabit assistant."

def get_slm_router_decision(query: str) -> str:
    """Determines if the query needs RAG or direct answer."""
    return Gatekeeper.get_routing_decision(query)

def process_and_ingest_file(file_path: str) -> Dict[str, Any]:
    """Ingests a file into the vector database with support for PDF, MD, and TXT."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    logger.info(f"Processing file for ingestion: {file_path}")
    
    try:
        if file_path.lower().endswith(".pdf"):
            from langchain_community.document_loaders import PyMuPDFLoader
            loader = PyMuPDFLoader(file_path)
        elif file_path.lower().endswith(".md"):
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            loader = UnstructuredMarkdownLoader(file_path)
        else:
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(file_path)
            
        docs = loader.load()
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        split_docs = text_splitter.split_documents(docs)
        
        embeddings = OllamaEmbeddings(model="mxbai-embed-large", base_url=SLM_URL)
        parsed = urlparse(DB_URL)
        adapter = ChromaAdapter(
            host=parsed.hostname or "localhost",
            port=parsed.port or 8000,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings
        )
        
        use_case = IngestUseCase(vector_store=adapter)
        
        chunks = [d.page_content for d in split_docs]
        metadatas = [d.metadata for d in split_docs]
        # Add filename to metadata if not present for citations
        for m in metadatas:
            if "source" not in m:
                m["source"] = os.path.basename(file_path)
        
        ids = [f"{os.path.basename(file_path)}_{i}" for i in range(len(split_docs))]
        
        use_case.ingest_text_chunks(chunks, metadatas, ids)
        
        return {"status": "success", "chunks": len(chunks)}
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        return {"status": "error", "message": str(e)}

def query_secure_slm(prompt: str, model_name: str = "qwen2.5:7b") -> Tuple[str, float]:
    """Secure direct SLM query with PII anonymization."""
    from .core.security import anonymize_text, deanonymize_text
    from .inference_factory import create_inference_provider
    
    # 1. Anonymize
    anon_result = anonymize_text(prompt)
    
    # 2. Generate
    adapter = create_inference_provider()
    result = adapter.generate(InferenceRequest(model=model_name, prompt=anon_result.sanitized_text))
    
    # 3. Deanonymize
    restored_text = deanonymize_text(result.text, anon_result.token_map)
    
    return restored_text, result.latency_seconds

def execute_rag_pipeline(query: str) -> str:
    """Legacy helper for RAG pipeline."""
    # We recreate the context here to avoid circular imports with main.py factories
    embeddings = OllamaEmbeddings(model="mxbai-embed-large", base_url=SLM_URL)
    parsed = urlparse(DB_URL)
    vector_store = ChromaAdapter(
        host=parsed.hostname or "localhost",
        port=parsed.port or 8000,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings
    )
    inference_provider = OllamaInferenceAdapter(endpoint=f"{SLM_URL}/api/generate")
    
    use_case = ChatUseCase(
        inference_provider=inference_provider,
        vector_store=vector_store,
        system_prompt=load_system_prompt()
    )
    
    # Using a default model name or taking from env
    model_name = os.getenv("MODEL_NAME", "qwen2.5:7b")
    response, _, _ = use_case.execute_rag(query, model_name)
    return response

# Internal helpers for legacy tests compatibility
def _create_embeddings():
    return OllamaEmbeddings(model="mxbai-embed-large", base_url=SLM_URL)

def _get_chroma_collection():
    parsed = urlparse(DB_URL)
    return ChromaAdapter(
        host=parsed.hostname or "localhost",
        port=parsed.port or 8000,
        collection_name=COLLECTION_NAME,
        embedding_function=_create_embeddings()
    )
