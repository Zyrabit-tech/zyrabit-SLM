import logging
import os
import re
import tempfile
import time
import uuid
from typing import Optional
from . import services
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from . import mcp_bridge
from .adapters.n8n_adapter import N8nAdapter, N8nIntegrationPolicy

# --- CONFIGURATION ---
# Reads environment variables. Ensure you have a .env file or export them.
# Default for local development
SLM_URL = os.getenv("SLM_URL", "http://localhost:11434")
# Default for local ChromaDB
DB_URL = os.getenv("DB_URL", "http://localhost:8000")
logger = logging.getLogger("uvicorn.error")

# --- FastAPI Initialization ---
app = FastAPI(
    title="RAG-Ops Framework API",
    description="An API to orchestrate decisions between RAG and direct SLM calls.",
    version="0.1.0",
)

_instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=False,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/docs", "/openapi.json"],
)
_instrumentator.instrument(app)
_instrumentator.expose(app, include_in_schema=False)
n8n_adapter = N8nAdapter(
    policy=N8nIntegrationPolicy.from_env(),
    execute_automation=services.execute_automation_request,
)

# --- DTOs (Data Transfer Objects) con Pydantic ---


class ChatQuery(BaseModel):
    text: str


class ChatResponse(BaseModel):
    response: str
    metadata: Optional[dict] = None

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


@app.get("/mcp/config.json", tags=["MCP"])
def mcp_config():
    return mcp_bridge.get_config()


@app.post("/mcp", tags=["MCP"])
async def mcp_jsonrpc(request: Request):
    try:
        payload = await request.json()
    except Exception:
        logger.exception("Invalid MCP JSON payload")
        raise HTTPException(status_code=400, detail="Invalid MCP JSON payload.")

    response, status_code = mcp_bridge.handle_jsonrpc(payload)
    return JSONResponse(content=response, status_code=status_code)


@app.post("/v1/integrations/n8n/webhook", tags=["Integrations"])
async def n8n_webhook(request: Request):
    """
    Receives n8n webhook calls through a secured integration adapter.
    """
    raw_body = await request.body()
    authorization_header = request.headers.get("authorization", "")
    signature_header = request.headers.get("x-zyrabit-signature", "")

    try:
        payload = await request.json()
    except Exception:
        logger.exception("Invalid n8n JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    try:
        n8n_adapter.authorize_request(
            authorization_header=authorization_header,
            signature_header=signature_header,
            raw_body=raw_body,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    try:
        result = n8n_adapter.handle_payload(payload)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/v1/chat", response_model=ChatResponse, tags=["Agentic Router"])
def chat_router(query: ChatQuery):
    """
    Main Agentic Router.

    This endpoint receives a query and decides the best way to answer it:
    1.  **search_rag_database**: Uses the RAG pipeline for specific knowledge.
    2.  **direct_SLM_answer**: Asks the SLM directly for general knowledge.
    3.  **reject_query**: Rejects the query if it is out of scope.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    # 1. The router decides what to do
    decision = services.get_slm_router_decision(query.text)
    logger.info(
        "Chat request routed request_id=%s decision=%s query_length=%s",
        request_id,
        decision,
        len(query.text or ""),
    )

    # 2. The "badass" if/elif/else executes the decision
    if decision == "search_rag_database":
        response_text, rag_hits = services.execute_rag_pipeline_with_metadata(query.text)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "Chat request completed request_id=%s decision=%s rag_hits=%s latency_ms=%s",
            request_id,
            decision,
            rag_hits,
            latency_ms,
        )
        return ChatResponse(
            response=response_text,
            metadata={
                "route_decision": decision,
                "rag_hits": rag_hits,
                "latency_ms": latency_ms,
            },
        )

    elif decision == "direct_SLM_answer":
        response_text = services.call_direct_slm(query.text)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "Chat request completed request_id=%s decision=%s rag_hits=0 latency_ms=%s",
            request_id,
            decision,
            latency_ms,
        )
        return ChatResponse(
            response=response_text,
            metadata={
                "route_decision": decision,
                "rag_hits": 0,
                "latency_ms": latency_ms,
            },
        )

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


@app.post("/v1/ingest", tags=["Ingestion"])
async def ingest_document(file: UploadFile = File(...)):
    """
    Endpoint to ingest PDF, TXT or Markdown documents into the knowledge base.

    - **Validation**: Only .pdf, .txt and .md files.
    - **Size**: Max 800MB (validated by server config, basic logic here).
    """
    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
    ALLOWED_MIME_BY_EXT = {
        ".pdf": {"application/pdf", "application/octet-stream"},
        ".txt": {"text/plain", "application/octet-stream"},
        ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    }
    MAX_SIZE_MB = 800
    CHUNK_SIZE_BYTES = 1024 * 1024  # 1MB
    ingest_id = str(uuid.uuid4())

    # 1. Validate extension
    original_filename = file.filename or "uploaded_file"
    file_ext = os.path.splitext(original_filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Solo se aceptan: {ALLOWED_EXTENSIONS}")

    content_type = (file.content_type or "").lower()
    allowed_mime_types = ALLOWED_MIME_BY_EXT[file_ext]
    if content_type and content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=400,
            detail=f"MIME no permitido para {file_ext}. Tipos aceptados: {sorted(allowed_mime_types)}",
        )

    # 2. Save temporarily for processing using a server-generated path
    temp_file_path = None
    try:
        total_size = 0
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=file_ext,
            prefix="ingest_",
            dir="/tmp",
            delete=False,
        ) as temp_file:
            temp_file_path = temp_file.name
            while True:
                chunk = await file.read(CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_SIZE_MB * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail=f"El archivo excede el tamaño máximo de {MAX_SIZE_MB}MB.",
                    )
                temp_file.write(chunk)

        # 3. Process ingestion
        result = services.process_and_ingest_file(temp_file_path)
        ui_filename = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(original_filename))
        ui_filename = ui_filename[:80] if ui_filename else "uploaded_file"
        result["filename"] = ui_filename
        result["ingest_id"] = ingest_id
        return result

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Ingest failed ingest_id=%s filename=%s content_type=%s temp_file_path=%s",
            ingest_id,
            original_filename,
            content_type,
            temp_file_path,
        )
        raise HTTPException(status_code=500, detail="Error procesando el archivo.")
    finally:
        await file.close()
        # Cleanup
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# To run locally with `uvicorn main:app --reload`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
