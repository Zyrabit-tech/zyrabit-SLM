import logging
import os
import socketio
from typing import Dict, Any, Tuple
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator
from urllib.parse import urlparse

# Hexagonal Imports
from .infrastructure.persistence.chroma_adapter import ChromaAdapter
from .domain.use_cases import ChatUseCase
from app.domain.services.gatekeeper import Gatekeeper
from .inference_factory import create_inference_provider
from . import services # Temporary until fully migrated

# --- CONFIGURATION ---
SLM_URL = os.getenv("SLM_URL", "http://zyrabit-engine:11434")
DB_URL = os.getenv("DB_URL", "http://zyrabit-db:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")
COLLECTION_NAME = os.getenv("RAG_COLLECTION", "zyrabit_knowledge")

logger = logging.getLogger("uvicorn.error")

# --- Dependency Factories ---
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

# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Phase
    from .auto_ingest import run_auto_ingest
    run_auto_ingest()
    yield
    # Shutdown Phase (placeholder)

# --- FastAPI & Socket.io Setup ---
app = FastAPI(
    title="Zyrabit SLM API",
    description="Hexagonal RAG-Ops API with Socket.io streaming.",
    version="1.4.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Instrumentation ---
Instrumentator().instrument(app).expose(app)

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
sio_app = socketio.ASGIApp(sio)

# --- Register Routers (Driving Adapters) ---
from app.api.v1.endpoints import chat, health, documents, mcp, integrations
app.include_router(chat.router, prefix="/v1", tags=["Chat"])
app.include_router(health.router, prefix="/v1", tags=["Monitoring"])
app.include_router(documents.router, prefix="/v1", tags=["Documents"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP"]) # Root-level as expected by some clients
app.include_router(integrations.router, prefix="/v1/integrations", tags=["Integrations"])

# --- Legacy Compatibility ---
INGEST_DIR = os.getenv("DOCS_DIR", "./document_source")

# --- Socket.io Events (Driving Adapter) ---
@sio.event
async def connect(sid, environ):
    logger.info(f"Socket connected: {sid}")

@sio.event
async def chat_message(sid, data):
    text = data.get("text", "")
    decision = Gatekeeper.get_routing_decision(text)
    
    if decision == "reject_query":
        await sio.emit("chat_response", {
            "response": "I'm sorry, query out of scope. Focusing on Zyrabit topics only.",
            "metadata": {"decision": "rejected"}
        }, to=sid)
        return

    try:
        use_case = get_chat_use_case()
        sources = []
        if decision == "search_rag_database":
            response, hits, latency, sources = use_case.execute_rag(text, MODEL_NAME)
        else:
            response, latency = use_case.execute_direct_chat(text, MODEL_NAME)
            hits = 0

        await sio.emit("chat_response", {
            "response": response,
            "metadata": {
                "decision": decision, 
                "rag_hits": hits, 
                "latency_ms": round(latency * 1000, 2),
                "sources": sources
            }
        }, to=sid)
    except Exception as e:
        logger.error(f"Error in chat_message handler: {e}")
        await sio.emit("chat_response", {
            "response": f"I encountered a secure gateway error: {str(e)}",
            "metadata": {"decision": "error", "latency_ms": 0, "rag_hits": 0, "sources": []}
        }, to=sid)

# --- Mounting & Static ---
app.mount("/socket.io", sio_app)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/v1/health")
