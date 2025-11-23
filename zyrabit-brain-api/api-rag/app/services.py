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
    Llama a un LLM para clasificar la consulta del usuario y decidir qué herramienta usar.
    """
    llm_url = os.environ.get("LLM_URL", "http://localhost:11434")
    
    prompt = ROUTER_META_PROMPT.format(query=query)
    
    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = httpx.post(f"{llm_url}/api/generate", json=payload, timeout=20)
        response.raise_for_status()  # Lanza una excepción para errores HTTP 4xx/5xx
        
        api_response = response.json()
        
        # Extrae y limpia la decisión del LLM
        decision = api_response.get("response", "").strip()
        
        # Un pequeño guardrail por si el LLM responde algo inesperado
        allowed_decisions = ["search_rag_database", "direct_llm_answer", "reject_query"]
        if decision in allowed_decisions:
            return decision
        else:
            # Si el LLM no da una respuesta válida, usamos un fallback seguro.
            return "direct_llm_answer"
            
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        # En caso de error de red o HTTP, usamos un fallback seguro.
        print(f"Error al contactar al LLM: {e}")
        return "direct_llm_answer"


def execute_rag_pipeline(query: str) -> str:
    """
    Ejecuta el pipeline de Retrieval-Augmented Generation (RAG).
    1. Recupera contexto de ChromaDB.
    2. Aumenta un prompt con ese contexto.
    3. Genera una respuesta con un LLM.
    """
    db_url = os.environ.get("DB_URL", "http://localhost:8000")
    llm_url = os.environ.get("LLM_URL", "http://localhost:11434")

    try:
        # 1. Conectar y buscar en ChromaDB
        parsed_url = urlparse(db_url)
        chroma_client = chromadb.HttpClient(host=parsed_url.hostname, port=parsed_url.port)
        collection = chroma_client.get_or_create_collection("libros_tecnicos")
        
        results = collection.query(query_texts=[query], n_results=5)
        context_documents = results.get('documents', [[]])[0]
        context = "\n".join(context_documents)

        # 2. Construir el megaprompt
        augmented_prompt = RAG_MEGA_PROMPT.format(context=context, query=query)

        # 3. Llamar al LLM con el prompt aumentado
        payload = {
            "model": "mistral",
            "prompt": augmented_prompt,
            "stream": False
        }
        
        response = httpx.post(f"{llm_url}/api/generate", json=payload, timeout=30)
        response.raise_for_status()
        
        api_response = response.json()
        return api_response.get("response", "").strip()

    except Exception as e:
        print(f"Error en el pipeline RAG: {e}")
        return "Lo siento, ocurrió un error al procesar tu consulta con la base de datos de conocimiento."


def call_direct_llm(query: str) -> str:
    """
    Llama directamente a un LLM (Ollama) con la consulta del usuario.
    """
    llm_url = os.environ.get("LLM_URL", "http://localhost:11434")
    
    payload = {
        "model": "mistral", # Usamos el mismo modelo que para el router
        "prompt": query,    # El prompt es directamente la consulta del usuario
        "stream": False
    }
    
    try:
        response = httpx.post(f"{llm_url}/api/generate", json=payload, timeout=20)
        response.raise_for_status()
        
        api_response = response.json()
        
        # Extrae y limpia la respuesta del LLM
        return api_response.get("response", "").strip()
            
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"Error al contactar al LLM para respuesta directa: {e}")
        return "Lo siento, no pude contactar al LLM para responder a tu pregunta."