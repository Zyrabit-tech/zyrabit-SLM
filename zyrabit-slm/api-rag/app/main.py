import logging
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

# Infrastructure / Shared
from app.infrastructure.shared.config import PROJECT_NAME, API_V1_STR
from app.infrastructure.shared import metrics
from app.infrastructure.shared.state_tracker import IngestionTracker

# Infrastructure Adapters
from app.infrastructure.persistence.chroma_adapter import ChromaAdapter
from app.infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter
from app.infrastructure.shared.config import SLM_URL, DB_URL, RAG_COLLECTION

logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    KISS Lifespan: Manages adapter initialization and graceful shutdown.
    """
    logger.info("🚀 Zyrabit SLM API Starting...")
    
    # 1. Initialize Adapters
    # In a real production app, we'd use factories here. 
    # For MVP V3.0, we instantiate directly and inject into app.state.
    
    try:
        # 0. Initialize State Tracker
        IngestionTracker.init_db()
        
        # 0.1 Prepare Embeddings (Secondary Adapter)
        from langchain_ollama import OllamaEmbeddings
        embeddings = OllamaEmbeddings(
            model="mxbai-embed-large",
            base_url=SLM_URL
        )

        # Persistence
        app.state.vector_store = ChromaAdapter(
            host="zyrabit-db",
            port=8000,
            collection_name=RAG_COLLECTION,
            embedding_function=embeddings
        )
        
        # 0.5 Self-Healing: Clean up stale ingests
        stale_ids = IngestionTracker.get_stale_ingests()
        if stale_ids:
            logger.warning(f"🧹 Found {len(stale_ids)} stale ingests. Cleaning up...")
            for doc_id in stale_ids:
                app.state.vector_store.delete(where={"doc_id": doc_id})
                IngestionTracker.clear_stale(doc_id)
            logger.info("✅ Cleanup completed.")

        # 1. Inference
        app.state.inference_provider = OllamaInferenceAdapter(
            endpoint=f"{SLM_URL}/api/generate"
        )
        
        # 2. Startup Phase (Auto-Ingest)
        from app.auto_ingest import run_auto_ingest
        run_auto_ingest(app.state.vector_store)
        
        logger.info("✅ Adapters and Auto-Ingest initialized.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize adapters: {e}")
        # In strict mode, we might want to prevent startup, 
        # but for now we'll log and continue.

    yield
    
    # 2. Graceful Shutdown
    logger.info("🛑 Zyrabit SLM API Shutting down...")
    # Clean up connections if necessary
    # Example: await app.state.vector_store.close()

# --- FastAPI Setup ---
app = FastAPI(
    title=PROJECT_NAME,
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

# --- Socket.io Setup ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
sio_app = socketio.ASGIApp(sio)
app.mount("/socket.io", sio_app)

# --- Register Routers ---
from app.api.v1.endpoints import chat, health
app.include_router(chat.router, prefix=API_V1_STR, tags=["Chat"])
app.include_router(health.router, prefix=API_V1_STR, tags=["Monitoring"])

# --- Socket.io Events (Bridge to Use Cases) ---
@sio.event
async def connect(sid, environ):
    logger.info(f"Socket connected: {sid}")

@sio.event
async def chat_message(sid, data):
    # This will be refactored in Phase 3 to use the ChatUseCase
    # from the container/app.state
    pass

@app.get("/", include_in_schema=False)
async def root():
    return {"status": "Zyrabit SLM API is running. Visit /docs for documentation."}
