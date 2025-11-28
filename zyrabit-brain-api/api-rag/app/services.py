import os
import httpx
import chromadb
from urllib.parse import urlparse

ROUTER_META_PROMPT = """Tus herramientas son: [search_rag_database, direct_llm_answer, reject_query].
Debes clasificar la siguiente consulta del usuario en una de esas herramientas.
Responde SÓLO con el nombre de la herramienta.

Consulta del usuario:
---
{query}
---
"""

RAG_MEGA_PROMPT = """Basado en el siguiente contexto de una base de datos de conocimiento, responde a la pregunta del usuario.
Sé conciso y directo, basándote únicamente en el contexto proporcionado.

Contexto:
---
{context}
---

Pregunta del usuario:
---
{query}
---
"""


def get_llm_router_decision(query: str) -> str:
    """
    Calls an LLM to classify the user query and decide which tool to use.
    """
    llm_url = os.environ.get("LLM_URL", "http://localhost:11434")

    prompt = ROUTER_META_PROMPT.format(query=query)

    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = httpx.post(
            f"{llm_url}/api/generate",
            json=payload,
            timeout=20)
        response.raise_for_status()  # Raises an exception for HTTP 4xx/5xx errors

        api_response = response.json()

        # Extracts and cleans the LLM decision
        decision = api_response.get("response", "").strip()

        # A small guardrail in case the LLM responds with something unexpected
        allowed_decisions = [
            "search_rag_database",
            "direct_llm_answer",
            "reject_query"]
        if decision in allowed_decisions:
            return decision
        else:
            # If the LLM does not give a valid response, we use a safe
            # fallback.
            return "direct_llm_answer"

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        # In case of network or HTTP error, we use a safe fallback.
        print(f"Error al contactar al LLM: {e}")
        return "direct_llm_answer"


def execute_rag_pipeline(query: str) -> str:
    """
    Executes the Retrieval-Augmented Generation (RAG) pipeline.
    1. Retrieves context from ChromaDB.
    2. Augments a prompt with that context.
    3. Generates a response with an LLM.
    """
    db_url = os.environ.get("DB_URL", "http://localhost:8000")
    llm_url = os.environ.get("LLM_URL", "http://localhost:11434")

    try:
        # 1. Connect and search in ChromaDB
        parsed_url = urlparse(db_url)
        chroma_client = chromadb.HttpClient(
            host=parsed_url.hostname, port=parsed_url.port)
        collection = chroma_client.get_or_create_collection("libros_tecnicos")

        results = collection.query(query_texts=[query], n_results=5)
        context_documents = results.get('documents', [[]])[0]
        context = "\n".join(context_documents)

        # 2. Build the megaprompt
        augmented_prompt = RAG_MEGA_PROMPT.format(context=context, query=query)

        # 3. Call the LLM with the augmented prompt
        payload = {
            "model": "mistral",
            "prompt": augmented_prompt,
            "stream": False
        }

        response = httpx.post(
            f"{llm_url}/api/generate",
            json=payload,
            timeout=30)
        response.raise_for_status()

        api_response = response.json()
        return api_response.get("response", "").strip()

    except Exception as e:
        print(f"Error en el pipeline RAG: {e}")
        return "Lo siento, ocurrió un error al procesar tu consulta con la base de datos de conocimiento."


def call_direct_llm(query: str) -> str:
    """
    Calls an LLM (Ollama) directly with the user query.
    """
    llm_url = os.environ.get("LLM_URL", "http://localhost:11434")

    payload = {
        "model": "mistral",  # We use the same model as for the router
        "prompt": query,    # The prompt is directly the user query
        "stream": False
    }

    try:
        response = httpx.post(
            f"{llm_url}/api/generate",
            json=payload,
            timeout=20)
        response.raise_for_status()

        api_response = response.json()

        # Extracts and cleans the LLM response
        return api_response.get("response", "").strip()

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"Error al contactar al LLM para respuesta directa: {e}")
        return "Lo siento, no pude contactar al LLM para responder a tu pregunta."


def process_and_ingest_file(file_path: str) -> dict:
    """
    Processes a file (PDF) and ingests its embeddings into ChromaDB.
    """
    from langchain_community.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_ollama import OllamaEmbeddings

    db_url = os.environ.get("DB_URL", "http://localhost:8000")

    try:
        # 1. Load the document
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        # 2. Split into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(documents)

        # 3. Generate Embeddings and save to ChromaDB
        # We use langchain-ollama to generate embeddings with mxbai-embed-large
        embeddings = OllamaEmbeddings(model="mxbai-embed-large")

        parsed_url = urlparse(db_url)
        chroma_client = chromadb.HttpClient(
            host=parsed_url.hostname, port=parsed_url.port)
        collection = chroma_client.get_or_create_collection("libros_tecnicos")

        # Prepare data for ChromaDB
        ids = [f"doc_{i}" for i in range(len(chunks))]
        texts = [chunk.page_content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        # Generate embeddings manually if we don't use Langchain's direct integration with Chroma
        # But for simplicity and control, we can use the collection directly if we have the embeddings
        # Or let Chroma calculate if it has the embedding function configured.
        # Here we assume Chroma does NOT have the embedding function configured on the server,
        # so we calculate them ourselves.

        embedded_texts = embeddings.embed_documents(texts)

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embedded_texts,
            metadatas=metadatas
        )

        return {
            "status": "success",
            "chunks_processed": len(chunks),
            "message": "Documento ingestada correctamente en la base de conocimiento."}

    except Exception as e:
        print(f"Error en la ingesta: {e}")
        raise e
