import logging
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

# Infrastructure / Shared
from app.infrastructure.shared.config import PROJECT_NAME, API_V1_STR, SLM_URL, DB_HOST, DB_PORT, RAG_COLLECTION
from app.infrastructure.shared import metrics
from app.infrastructure.shared.state_tracker import IngestionTracker

# Infrastructure Adapters
from app.infrastructure.persistence.chroma_adapter import ChromaAdapter
from app.infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter

# Industrial Logging Standard
from app.infrastructure.shared.logger import setup_logging
setup_logging()
logger = logging.getLogger("zyrabit.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Resilient Lifespan: Ensures app.state is always consistent.
    """
    logger.info("🚀 Zyrabit SLM API Starting...")
    
    # 0. Pre-initialize state to avoid AttributeErrors
    app.state.vector_store = None
    app.state.inference_provider = None
    
    # 1. Initialize State Tracker
    try:
        IngestionTracker.init_db()
    except Exception as e:
        logger.error(f"❌ State Tracker failure: {e}")

    # 2. Initialize Vector Store (Chroma)
    try:
        app.state.vector_store = ChromaAdapter(
            host=DB_HOST,
            port=DB_PORT,
            collection_name=RAG_COLLECTION
        )
        logger.info("✅ Vector Store Adapter initialized.")
        
        # 2.1 Auto-Ingest
        from app.auto_ingest import run_auto_ingest
        await run_auto_ingest(app.state.vector_store)
        
    except Exception as e:
        logger.error(f"⚠️ Vector Store initialization failed: {e}")

    # 3. Initialize Inference Provider (Ollama)
    try:
        app.state.inference_provider = OllamaInferenceAdapter(
            endpoint=f"{SLM_URL}/api/generate"
        )
        logger.info("✅ Inference Provider initialized.")
    except Exception as e:
        logger.error(f"❌ Inference Provider failure: {e}")

    yield
    
    logger.info("🛑 Zyrabit SLM API Shutting down...")

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

# --- Socket.io Events ---
@sio.event
async def connect(sid, environ):
    logger.info(f"Socket connected: {sid}")

@app.get("/", include_in_schema=False)
async def root():
    return {"status": "Zyrabit SLM API is running. Visit /docs for documentation."}
