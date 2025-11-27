import os
from . import services
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, UploadFile, File
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

@app.get("/", include_in_schema=False)
async def root():
    """
    Redirige la raíz a la documentación interactiva.
    """
    return RedirectResponse(url="/docs")

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
@app.get("/metrics", tags=["Monitoring"])
def get_metrics():
    """
    Endpoint para Prometheus.
    """
    return {"status": "ok", "message": "Metrics endpoint (implementar métricas reales aquí)"}


@app.post("/v1/ingest", tags=["Ingestion"])
async def ingest_document(file: UploadFile = File(...)):
    """
    Endpoint para ingestar documentos PDF a la base de conocimiento.
    
    - **Validación**: Solo archivos .pdf y .docx (por ahora solo PDF implementado).
    - **Tamaño**: Máximo 800MB (validado por configuración del servidor, aquí lógica básica).
    """
    ALLOWED_EXTENSIONS = {".pdf"}
    MAX_SIZE_MB = 800
    
    # 1. Validar extensión
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido. Solo se aceptan: {ALLOWED_EXTENSIONS}")
    
    # 2. Guardar temporalmente para procesar
    temp_file_path = f"/tmp/{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            # Podríamos leer en chunks para validar tamaño, pero por simplicidad:
            content = await file.read()
            if len(content) > MAX_SIZE_MB * 1024 * 1024:
                 raise HTTPException(status_code=400, detail=f"El archivo excede el tamaño máximo de {MAX_SIZE_MB}MB.")
            buffer.write(content)
            
        # 3. Procesar ingesta
        result = services.process_and_ingest_file(temp_file_path)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {str(e)}")
    finally:
        # Limpieza
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# Para ejecutar localmente con `uvicorn main:app --reload`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
