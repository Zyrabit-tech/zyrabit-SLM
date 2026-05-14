import logging
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

# Infrastructure / Shared
from app.infrastructure.shared.config import PROJECT_NAME, API_V1_STR, SLM_URL, RAG_COLLECTION, EMBEDDING_MODEL
from app.infrastructure.shared.logger import setup_logging
from app.infrastructure.shared.state_tracker import IngestionTracker

# Infrastructure Adapters
from app.infrastructure.persistence.chroma_adapter import ChromaAdapter, DirectOllamaEmbeddings
from app.infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter
from app.domain.services.retriever_service import HybridRetrieverService
from langchain_chroma import Chroma

# Setup Socket.io
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio)

# Setup logging
setup_logging()
logger = logging.getLogger("zyrabit.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Orchestrates Infrastructure Startup and Shutdown.
    """
    # 0. Initialize State Tracker (SQLite for ingest tracking)
    try:
        IngestionTracker.init_db()
        logger.info("✅ State Tracker initialized.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize State Tracker: {e}")

    logger.info("🚀 Zyrabit SLM API Starting...")
    
    app.state.vector_store = None
    app.state.retriever_service = None
    app.state.inference_provider = None
    
    try:
        # 1. Direct Embeddings
        embeddings = DirectOllamaEmbeddings(model=EMBEDDING_MODEL, base_url=SLM_URL)
        
        # 2. Vector Store (LangChain Chroma)
        lc_chroma = Chroma(
            collection_name=RAG_COLLECTION,
            embedding_function=embeddings,
            persist_directory="./chroma_data"
        )
        app.state.vector_store = ChromaAdapter(lc_chroma)
        
        # 3. Hybrid Retriever Service
        app.state.retriever_service = HybridRetrieverService(lc_chroma)
        
        # 4. Inference
        app.state.inference_provider = OllamaInferenceAdapter(endpoint=f"{SLM_URL}/api/generate")
        
        # 5. Auto-Ingest
        from app.auto_ingest import run_auto_ingest
        await run_auto_ingest(app.state.vector_store, app.state.retriever_service)
        
        logger.info("✅ Infrastructure initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize infrastructure: {e}")

    yield
    logger.info("🛑 Zyrabit SLM API Shutting down...")

app = FastAPI(title=PROJECT_NAME, lifespan=lifespan)

# Middleware
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Metrics
Instrumentator().instrument(app).expose(app)

# Register Routers
from app.api.v1.endpoints import chat, health, mcp, documents, integrations
app.include_router(chat.router, prefix=API_V1_STR, tags=["Chat"])
app.include_router(health.router, prefix=API_V1_STR, tags=["Monitoring"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP"])
app.include_router(documents.router, prefix=API_V1_STR, tags=["Documents"])
app.include_router(integrations.router, prefix=API_V1_STR, tags=["Integrations"])

@app.get("/", include_in_schema=False)
async def root():
    return {"status": "Zyrabit SLM API is running."}
