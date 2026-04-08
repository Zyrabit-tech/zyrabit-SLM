import logging
import os
import socketio
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from urllib.parse import urlparse

# Hexagonal Imports
from .infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter
from .infrastructure.persistence.chroma_adapter import ChromaAdapter
from .domain.use_cases import ChatUseCase
from .domain.services.gatekeeper import Gatekeeper
from . import services # Temporary until fully migrated

# --- CONFIGURATION ---
SLM_URL = os.getenv("SLM_URL", "http://slm-engine:11434")
DB_URL = os.getenv("DB_URL", "http://vector-db:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")
COLLECTION_NAME = os.getenv("RAG_COLLECTION", "zyrabit_knowledge")

logger = logging.getLogger("uvicorn.error")

# --- Dependency Factories ---
def get_inference_adapter():
    return OllamaInferenceAdapter(endpoint=f"{SLM_URL}/api/generate")

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

# --- FastAPI & Socket.io Setup ---
app = FastAPI(
    title="Zyrabit SLM API",
    description="Hexagonal RAG-Ops API with Socket.io streaming.",
    version="1.3.0",
)

@app.on_event("startup")
async def startup_event():
    from .auto_ingest import run_auto_ingest
    run_auto_ingest()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
sio_app = socketio.ASGIApp(sio)

# --- Register Routers (Driving Adapters) ---
from .api.v1.endpoints import chat, health
app.include_router(chat.router, prefix="/v1", tags=["Chat"])
app.include_router(health.router, prefix="/v1", tags=["Monitoring"])

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

    use_case = get_chat_use_case()
    if decision == "search_rag_database":
        response, hits, latency = use_case.execute_rag(text, MODEL_NAME)
    else:
        response, latency = use_case.execute_direct_chat(text, MODEL_NAME)
        hits = 0

    await sio.emit("chat_response", {
        "response": response,
        "metadata": {"decision": decision, "rag_hits": hits, "latency_ms": round(latency * 1000, 2)}
    }, to=sid)

# --- Mounting & Static ---
app.mount("/socket.io", sio_app)

static_dir = "/app/web-ui/dist"
if not os.path.exists(static_dir):
    static_dir = os.path.join(os.path.dirname(__file__), "static")

if os.path.isdir(static_dir):
    app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/v1/health")
