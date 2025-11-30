import os
from . import services
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel

# --- CONFIGURATION ---
# Reads environment variables. Ensure you have a .env file or export them.
# Default for local development
SLM_URL = os.getenv("SLM_URL", "http://localhost:11434")
# Default for local ChromaDB
DB_URL = os.getenv("DB_URL", "http://localhost:8000")

# --- FastAPI Initialization ---
app = FastAPI(
    title="RAG-Ops Framework API",
    description="An API to orchestrate decisions between RAG and direct SLM calls.",
    version="0.1.0",
)

# --- DTOs (Data Transfer Objects) con Pydantic ---


class ChatQuery(BaseModel):
    text: str


class ChatResponse(BaseModel):
    response: str

# --- API Endpoints ---


@app.get("/", include_in_schema=False)
async def root():
    """
    Redirects root to interactive documentation.
    """
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Monitoring"])
def health_check():
    """
    Health check endpoint to verify the service is active.
    """
    return {"status": "ok", "SLM_url": SLM_URL, "db_url": DB_URL}


@app.post("/v1/chat", response_model=ChatResponse, tags=["Agentic Router"])
def chat_router(query: ChatQuery):
    """
    Main Agentic Router.

    This endpoint receives a query and decides the best way to answer it:
    1.  **search_rag_database**: Uses the RAG pipeline for specific knowledge.
    2.  **direct_SLM_answer**: Asks the SLM directly for general knowledge.
    3.  **reject_query**: Rejects the query if it is out of scope.
    """
    # 1. The router decides what to do
    decision = services.get_slm_router_decision(query.text)

    # 2. The "badass" if/elif/else executes the decision
    if decision == "search_rag_database":
        response_text = services.execute_rag_pipeline(query.text)
        return ChatResponse(response=response_text)

    elif decision == "direct_SLM_answer":
        response_text = services.call_direct_slm(query.text)
        return ChatResponse(response=response_text)

    elif decision == "reject_query":
        raise HTTPException(
            status_code=400,
            detail="Consulta fuera de alcance. Por favor, haz preguntas relacionadas con los temas permitidos."
        )

    # Fallback in case the decision is none of the expected ones
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: Decisión del router desconocida ('{decision}').")


@app.get("/metrics", tags=["Monitoring"])
def get_metrics():
    """
    Prometheus endpoint.
    """
    return {
        "status": "ok",
        "message": "Metrics endpoint (implementar métricas reales aquí)"}


@app.post("/v1/ingest", tags=["Ingestion"])
async def ingest_document(file: UploadFile = File(...)):
    """
    Endpoint to ingest PDF documents into the knowledge base.

    - **Validation**: Only .pdf and .docx files (only PDF implemented for now).
    - **Size**: Max 800MB (validated by server config, basic logic here).
    """
    ALLOWED_EXTENSIONS = {".pdf"}
    MAX_SIZE_MB = 800

    # 1. Validate extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Solo se aceptan: {ALLOWED_EXTENSIONS}")

    # 2. Save temporarily for processing
    temp_file_path = f"/tmp/{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            # We could read in chunks to validate size, but for simplicity:
            content = await file.read()
            if len(content) > MAX_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"El archivo excede el tamaño máximo de {MAX_SIZE_MB}MB.")
            buffer.write(content)

        # 3. Process ingestion
        result = services.process_and_ingest_file(temp_file_path)
        return result

    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error procesando el archivo: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# To run locally with `uvicorn main:app --reload`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
