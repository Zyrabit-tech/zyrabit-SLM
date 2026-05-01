import logging
import os
import socketio
import time
from typing import Dict, Any, Tuple
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

# Domain / Core Imports
from app.domain.services.gatekeeper import Gatekeeper
from app.core.config import MODEL_NAME
from app.core.factories import get_chat_use_case
from app.core.cache import get_cached_response, store_cached_response

logger = logging.getLogger("uvicorn.error")

# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Phase
    from app.auto_ingest import run_auto_ingest
    run_auto_ingest()
    yield

# --- FastAPI & Socket.io Setup ---
app = FastAPI(
    title="Zyrabit SLM API",
    description="Hexagonal RAG-Ops API with Socket.io streaming.",
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

# --- Register Routers ---
from app.api.v1.endpoints import chat, health, documents, mcp, integrations
app.include_router(chat.router, prefix="/v1", tags=["Chat"])
app.include_router(health.router, prefix="/v1", tags=["Monitoring"])
app.include_router(documents.router, prefix="/v1", tags=["Documents"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP"])
app.include_router(integrations.router, prefix="/v1/integrations", tags=["Integrations"])

# --- Socket.io Events ---
@sio.event
async def connect(sid, environ):
    logger.info(f"Socket connected: {sid}")

@sio.event
async def chat_message(sid, data):
    msg_id = data.get("client_msg_id")
    text = data.get("text", "")
    
    # Idempotency Check
    cached = get_cached_response(msg_id)
    if cached:
        await sio.emit("chat_response", cached, to=sid)
        return

    decision = Gatekeeper.get_routing_decision(text)
    
    if decision == "reject_query":
        response_data = {
            "response": "I'm sorry, query out of scope. Focusing on Zyrabit topics only.",
            "metadata": {"decision": "rejected"}
        }
        await sio.emit("chat_response", response_data, to=sid)
        return

    try:
        use_case = get_chat_use_case()
        sources = []
        if decision == "search_rag_database":
            response, hits, latency, sources = use_case.execute_rag(text, MODEL_NAME)
        else:
            response, latency = use_case.execute_direct_chat(text, MODEL_NAME)
            hits = 0

        response_data = {
            "response": response,
            "metadata": {
                "decision": decision, 
                "rag_hits": hits, 
                "latency_ms": round(latency * 1000, 2),
                "sources": sources
            }
        }

        store_cached_response(msg_id, response_data)
        await sio.emit("chat_response", response_data, to=sid)
        
    except Exception as e:
        logger.error(f"Error in chat_message handler: {e}")
        await sio.emit("chat_response", {
            "response": f"I encountered a secure gateway error: {str(e)}",
            "metadata": {"decision": "error", "latency_ms": 0, "rag_hits": 0, "sources": []}
        }, to=sid)

# --- Mounting ---
app.mount("/socket.io", sio_app)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/v1/health")
