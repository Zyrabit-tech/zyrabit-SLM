import logging
import os
import re
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


INGEST_DIR = os.getenv("INGEST_DIR", "/app/document_source")

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
ALLOWED_MIME_BY_EXT = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
}
MAX_SIZE_MB = 800
CHUNK_SIZE_BYTES = 1024 * 1024  # 1MB


def _validate_ingest_file(filename: str, content_type: str) -> tuple:
    """Validate file extension and MIME type. Returns (safe_filename, file_ext)."""
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Solo se aceptan: {ALLOWED_EXTENSIONS}")

    ct = (content_type or "").lower()
    allowed_mime_types = ALLOWED_MIME_BY_EXT[file_ext]
    if ct and ct not in allowed_mime_types:
        raise HTTPException(
            status_code=400,
            detail=f"MIME no permitido para {file_ext}. Tipos aceptados: {sorted(allowed_mime_types)}",
        )

    sanitized_basename = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(filename))
    stem, ext_part = os.path.splitext(sanitized_basename)
    safe_filename = (stem[:75] + ext_part) if sanitized_basename else f"uploaded_file{file_ext}"
    return safe_filename, file_ext


async def _save_to_vault(file: UploadFile, safe_filename: str, ingest_id: str) -> str:
    """Write uploaded file to vault with size limit and path traversal protection. Returns vault_path."""
    vault_path = os.path.join(INGEST_DIR, safe_filename)

    resolved_path = os.path.realpath(vault_path)
    resolved_vault = os.path.realpath(INGEST_DIR)
    if not resolved_path.startswith(resolved_vault + os.sep) and resolved_path != resolved_vault:
        logger.warning(
            "Path traversal attempt blocked ingest_id=%s filename=%s resolved=%s",
            ingest_id, safe_filename, resolved_path,
        )
        raise HTTPException(
            status_code=400,
            detail="Nombre de archivo no permitido (posible path traversal).",
        )

    os.makedirs(INGEST_DIR, exist_ok=True)
    total_size = 0
    with open(vault_path, "wb") as dest:
        while True:
            chunk = await file.read(CHUNK_SIZE_BYTES)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_SIZE_MB * 1024 * 1024:
                dest.close()
                if os.path.exists(vault_path):
                    os.remove(vault_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"El archivo excede el tamaño máximo de {MAX_SIZE_MB}MB.",
                )
            dest.write(chunk)

    logger.info(
        "File saved to vault ingest_id=%s path=%s size_bytes=%s",
        ingest_id, vault_path, total_size,
    )
    return vault_path


@app.post("/v1/ingest", tags=["Ingestion"])
async def ingest_document(file: UploadFile = File(...)):
    """
    Endpoint to ingest PDF, TXT or Markdown documents into the knowledge base.

    Files are persisted in the secure document vault for auditing and re-indexing.
    - **Validation**: Only .pdf, .txt and .md files.
    - **Size**: Max 800MB.
    """
    ingest_id = str(uuid.uuid4())
    original_filename = file.filename or "uploaded_file"
    content_type = file.content_type or ""

    safe_filename, _ = _validate_ingest_file(original_filename, content_type)

    try:
        vault_path = await _save_to_vault(file, safe_filename, ingest_id)
        result = services.process_and_ingest_file(vault_path)
        result["filename"] = safe_filename
        result["ingest_id"] = ingest_id
        return result

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Ingest failed ingest_id=%s filename=%s content_type=%s",
            ingest_id,
            original_filename,
            content_type,
        )
        raise HTTPException(status_code=500, detail="Error procesando el archivo.")
    finally:
        await file.close()


@app.get("/v1/documents", tags=["Ingestion"])
def list_documents():
    """
    Lists all documents currently stored in the secure document vault.
    """
    vault_path = os.path.realpath(INGEST_DIR)
    if not os.path.isdir(vault_path):
        return {"documents": [], "total": 0}

    docs = []
    for entry in sorted(os.listdir(vault_path)):
        if entry.startswith("."):
            continue
        full_path = os.path.join(vault_path, entry)
        if os.path.isfile(full_path):
            stat = os.stat(full_path)
            docs.append({
                "filename": entry,
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime,
            })
    return {"documents": docs, "total": len(docs)}

# To run locally with `uvicorn main:app --reload`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
