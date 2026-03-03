import os
import re
from typing import Tuple
from urllib.parse import urlparse

from .inference_factory import create_inference_provider
from .metrics import (
    approximate_token_count,
    observe_latency_per_token,
    observe_security_hits,
    observe_token_usage,
)
from .ports.inference_port import InferenceProviderError, InferenceRequest
from .security import PipelineContext, build_security_pipeline

# --- CONFIGURATION ---
# Use environment variables or default to local settings
# Defaulting to phi3 as per setup script, but overridable.
MODEL_NAME = os.getenv("MODEL_NAME", "phi3")
DB_URL = os.getenv("DB_URL", "http://vector-db:8000")
COLLECTION_NAME = os.getenv("RAG_COLLECTION", "zyrabit_knowledge")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
RAG_N_RESULTS = 5

# Spam/off-topic patterns that trigger reject_query
REJECT_PATTERNS = [
    r"\bviagra\b", r"\bcasino\b", r"\bcrypto\s*scam\b",
    r"comprar\s+barato\s+ahora", r"click\s+here\s+now",
]

# --- SYSTEM PROMPT LOADING ---
def load_system_prompt() -> str:
    """Loads the system prompt from the txt file.
    
    Returns:
        str: The system prompt content, or empty string if file not found.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"⚠️  WARNING: system_prompt.txt not found at {prompt_path}")
        return ""

# Load system prompt once at module initialization
SYSTEM_PROMPT = load_system_prompt()

def print_header(title: str):
    """Prints a styled header to the console."""
    print(f"\n{'='*60}")
    print(f"🛡️ ZYRABIT SECURITY LAYER: {title}")
    print(f"{'='*60}")

def query_secure_slm(prompt: str) -> tuple[str, float]:
    """
    Sends a sanitized prompt to the local SLM and returns the response and latency.
    
    Args:
        prompt (str): The user's input prompt.
        
    Returns:
        tuple[str, float]: A tuple containing the (response_text, latency_in_seconds).
    """
    # PHASE A: SANITIZATION (Interceptor pipeline)
    pipeline = build_security_pipeline()
    pipeline_context = PipelineContext()
    sanitized_prompt = pipeline.process_request(prompt, pipeline_context)
    observe_security_hits(pipeline_context.detected_entities)

    if pipeline_context.token_map:
        print(f"   ⚠️  THREAT DETECTED. DATA REDACTED.")
        print(f"   SENT:     {sanitized_prompt}")
    else:
        print("   ✅ Input clean. Forwarding to core.")

    # PHASE B: LOCAL INFERENCE (Air-Gapped)
    # Construct prompt with system context
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {sanitized_prompt}\nAssistant:" if SYSTEM_PROMPT else sanitized_prompt
    
    try:
        provider = create_inference_provider()
        model_name = os.getenv("MODEL_NAME", MODEL_NAME)
        result = provider.generate(
            InferenceRequest(
                model=model_name,
                prompt=full_prompt,
                stream=False,
            )
        )
        masked_response = result.text
        restored_response = pipeline.process_response(masked_response, pipeline_context)
        latency = result.latency_seconds

        input_tokens = approximate_token_count(prompt)
        output_tokens = approximate_token_count(restored_response)
        observe_token_usage(input_tokens=input_tokens, output_tokens=output_tokens)
        observe_latency_per_token(latency_seconds=latency, output_tokens=output_tokens)

        return restored_response, latency

    except InferenceProviderError as exc:
        return f"❌ ERROR: {exc}", 0.0

def call_direct_slm(prompt: str) -> str:
    """
    Direct call to SLM without sanitization (for general knowledge).
    """
    response, _ = query_secure_slm(prompt)
    return response

def _parse_db_url(url: str) -> tuple[str, int]:
    """Parse DB_URL into (host, port) for ChromaDB HttpClient."""
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8000
    return host, port


def get_slm_router_decision(text: str) -> str:
    """
    Decides whether to use RAG, Direct SLM, or reject.
    Keyword-based router with spam detection.
    """
    text_lower = text.lower()
    # Reject spam/off-topic
    for pattern in REJECT_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return "reject_query"
    # RAG for project/tech topics
    keywords = ["zyrabit", "architecture", "security", "slm", "rag", "chromadb", "ollama", "docker"]
    if any(k in text_lower for k in keywords):
        return "search_rag_database"
    return "direct_SLM_answer"


def execute_rag_pipeline_with_metadata(text: str) -> Tuple[str, int]:
    """
    Executes the RAG pipeline: Retrieve -> Augment -> Generate.
    Uses ChromaDB for retrieval and Ollama for generation.
    """
    try:
        import chromadb
        from langchain_community.embeddings import OllamaEmbeddings

        host, port = _parse_db_url(DB_URL)
        client = chromadb.HttpClient(host=host, port=port)
        collection = client.get_or_create_collection(name=COLLECTION_NAME)

        embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        query_embedding = embeddings.embed_query(text)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=RAG_N_RESULTS,
        )

        docs = results.get("documents", [[]])
        rag_hits = 0
        if docs and docs[0]:
            context = "\n\n".join(docs[0])
            rag_hits = len(docs[0])
        else:
            context = "No relevant documents found in the knowledge base."

        augmented_prompt = f"Context from knowledge base:\n{context}\n\nQuestion: {text}\n\nAnswer based on the context:"
        response, _ = query_secure_slm(augmented_prompt)
        return response, rag_hits

    except Exception as e:
        return (
            f"Lo siento, ocurrió un error al procesar tu consulta con la base de datos "
            f"de conocimiento: {str(e)}"
        ), 0


def execute_rag_pipeline(text: str) -> str:
    """
    Backward-compatible wrapper for existing callers/tests.
    """
    response, _ = execute_rag_pipeline_with_metadata(text)
    return response


def process_and_ingest_file(file_path: str) -> dict:
    """
    Ingest PDF or TXT file into ChromaDB.
    Returns status dict with chunks_processed.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        docs = loader.load()
    elif ext in (".txt", ".md"):
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if not docs:
        return {"status": "success", "filename": os.path.basename(file_path), "chunks_processed": 0}

    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import OllamaEmbeddings
    import chromadb

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = text_splitter.split_documents(docs)

    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    documents_to_add = [c.page_content for c in chunks]
    metadatas_to_add = [c.metadata for c in chunks]
    embedded_chunks = embeddings.embed_documents(documents_to_add)

    host, port = _parse_db_url(DB_URL)
    client = chromadb.HttpClient(host=host, port=port)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    ids = [f"chunk_{abs(hash(c.page_content)) % 10**10}_{i}" for i, c in enumerate(chunks)]
    collection.add(
        embeddings=embedded_chunks,
        documents=documents_to_add,
        metadatas=metadatas_to_add,
        ids=ids,
    )

    return {
        "status": "success",
        "filename": os.path.basename(file_path),
        "chunks_processed": len(chunks),
        "message": "Documento ingestado correctamente en la base de conocimiento.",
    }


def execute_automation_request(text: str) -> str:
    """
    Executes automation-originated requests using the same routing rules as chat.
    """
    decision = get_slm_router_decision(text)
    if decision == "search_rag_database":
        return execute_rag_pipeline(text)
    if decision == "direct_SLM_answer":
        return call_direct_slm(text)
    return "Automation request rejected by router policy."

# --- EXECUTION ---
if __name__ == "__main__":
    print_header("INITIATING ZERO-TRUST PROTOCOL")

    # CASE 1: HARMLESS QUERY
    query_1 = "What is the capital of France?"
    print(f"\n🗣️  User: {query_1}")
    response, latency = query_secure_slm(query_1)
    print(f"🤖 Zyrabit ({latency:.2f}s): {response.strip()}")

    # CASE 2: DATA LEAK ATTEMPT (Whisper Leak Scenario)
    query_2 = "Draft an email confirming I transferred $50,000.00 USD to account 4532-1234-5678-9012 using my credentials."
    print(f"\n🗣️  User (Risky): {query_2}")
    response, latency = query_secure_slm(query_2)
    
    print_header("SECURE MODEL RESPONSE")
    print(f"🤖 Zyrabit ({latency:.2f}s): {response.strip()}")
