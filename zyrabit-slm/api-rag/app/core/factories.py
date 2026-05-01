from urllib.parse import urlparse
from app.core.config import SLM_URL, DB_URL, COLLECTION_NAME
from app.infrastructure.persistence.chroma_adapter import ChromaAdapter
from app.domain.use_cases import ChatUseCase
from app.inference_factory import create_inference_provider
import app.services as services

def get_inference_adapter():
    return create_inference_provider()

def get_vector_store_adapter():
    from langchain_ollama import OllamaEmbeddings
    embeddings = OllamaEmbeddings(model="mxbai-embed-large", base_url=SLM_URL)
    parsed = urlparse(DB_URL)
    return ChromaAdapter(
        host=parsed.hostname or "localhost",
        port=parsed.port or 8000,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings
    )

def get_chat_use_case():
    system_prompt = services.load_system_prompt()
    return ChatUseCase(
        inference_provider=get_inference_adapter(),
        vector_store=get_vector_store_adapter(),
        system_prompt=system_prompt
    )
