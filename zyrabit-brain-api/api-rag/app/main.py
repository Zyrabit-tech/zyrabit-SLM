import os
from . import services
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- Configuración ---
# Lee las variables de entorno. Asegúrate de tener un .env o de exportarlas.
LLM_URL = os.getenv("LLM_URL", "http://localhost:11434") # Default para desarrollo local
DB_URL = os.getenv("DB_URL", "http://localhost:8000") # Default para ChromaDB local

# --- Inicialización de FastAPI ---
app = FastAPI(
    title="RAG-Ops Framework API",
    description="Una API para orquestar decisiones entre RAG y llamadas directas a LLM.",
    version="0.1.0",
)

# --- DTOs (Data Transfer Objects) con Pydantic ---
class ChatQuery(BaseModel):
    text: str

class ChatResponse(BaseModel):
    response: str

# --- Endpoints de la API ---

@app.get("/health", tags=["Monitoring"])
def health_check():
    """
    Endpoint de salud para verificar que el servicio está activo.
    """
    return {"status": "ok", "llm_url": LLM_URL, "db_url": DB_URL}

@app.post("/v1/chat", response_model=ChatResponse, tags=["Agentic Router"])
def chat_router(query: ChatQuery):
    """
    Router Agéntico Principal.

    Este endpoint recibe una consulta y decide la mejor manera de responderla:
    1.  **search_rag_database**: Usa el pipeline RAG para conocimiento específico.
    2.  **direct_llm_answer**: Pregunta directamente al LLM para conocimiento general.
    3.  **reject_query**: Rechaza la consulta si está fuera de alcance.
    """
    # 1. El router decide qué hacer
    decision = services.get_llm_router_decision(query.text)

    # 2. El `if/elif/else` "chingón" ejecuta la decisión
    if decision == "search_rag_database":
        response_text = services.execute_rag_pipeline(query.text)
        return ChatResponse(response=response_text)

    elif decision == "direct_llm_answer":
        response_text = services.call_direct_llm(query.text)
        return ChatResponse(response=response_text)

    elif decision == "reject_query":
        raise HTTPException(
            status_code=400,
            detail="Consulta fuera de alcance. Por favor, haz preguntas relacionadas con los temas permitidos."
        )
    
    # Fallback por si la decisión no es ninguna de las esperadas
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: Decisión del router desconocida ('{decision}')."
        )

# Para ejecutar localmente con `uvicorn main:app --reload`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
