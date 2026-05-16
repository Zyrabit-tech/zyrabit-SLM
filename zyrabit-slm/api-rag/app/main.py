import asyncio
import os
import logging
# pyrefly: ignore [missing-import]
import socketio
# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
# pyrefly: ignore [missing-import]
from prometheus_fastapi_instrumentator import Instrumentator

# Infrastructure / Shared
from app.infrastructure.shared.config import (
    PROJECT_NAME, API_V1_STR, SLM_URL, 
    RAG_COLLECTION, EMBEDDING_MODEL, DB_HOST, DB_PORT
)
from app.infrastructure.shared.logger import setup_logging
from app.infrastructure.shared.state_tracker import SovereignStateManager
from app.infrastructure.shared.cache import global_cache

# Domain Layer
from app.domain.services.gatekeeper import Gatekeeper
from app.domain.use_cases.chat_use_case import ChatUseCase
from app.domain.use_cases.ingest_use_case import IngestUseCase
from app.domain.services.mcp_service import mcp

# Infrastructure Adapters
from app.infrastructure.persistence.chroma_adapter import ChromaAdapter, DirectOllamaEmbeddings
from app.infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter
from app.domain.services.retriever_service import HybridRetrieverService
# pyrefly: ignore [missing-import]
from langchain_chroma import Chroma

# Setup Socket.io (V5.2 Fix: Correct path mapping)
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
# By setting socketio_path to empty string, we tell the ASGI app to handle
# the requests directly at the mount point.
socket_app = socketio.ASGIApp(sio, socketio_path='')

# Setup logging
setup_logging()
logger = logging.getLogger("zyrabit.api")

# Global App State Reference for Sockets
_global_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    V5.0 Lifespan: Orchestrates the Sovereign AI Infrastructure.
    """
    global _global_app
    _global_app = app
    app.state.sio = sio # Store for other endpoints
    # 0. Initialize Sovereign State
    try:
        # Use the configured DB_PATH (from env or default)
        SovereignStateManager.init_db()
        logger.info(f"✅ Sovereign State initialized at {SovereignStateManager.DB_PATH}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Sovereign State: {e}")


    logger.info("🚀 Zyrabit SLM API Starting...")
    
    if os.getenv("TESTING") == "true":
        logger.info("🧪 Test Mode: Skipping heavy infrastructure initialization.")
        yield
        return

    try:
        # 1. Direct Embeddings
        embeddings = DirectOllamaEmbeddings(model=EMBEDDING_MODEL, base_url=SLM_URL)
        
        # 2. Vector Store (Connecting to remote Chroma Server)
        import chromadb
        # Use HttpClient to connect to the zyrabit-db container
        chroma_client = chromadb.HttpClient(host=DB_HOST, port=DB_PORT)
        
        lc_chroma = Chroma(
            client=chroma_client,
            collection_name=RAG_COLLECTION,
            embedding_function=embeddings
        )
        app.state.vector_store = ChromaAdapter(lc_chroma)
        
        # 3. Hybrid Retriever
        app.state.retriever_service = HybridRetrieverService(lc_chroma)
        
        # 4. Inference Provider
        app.state.inference_provider = OllamaInferenceAdapter(endpoint=f"{SLM_URL}/api/generate")
        
        # 5. Use Cases (Singletons for the session)
        app.state.chat_use_case = ChatUseCase(
            inference_provider=app.state.inference_provider,
            retriever_service=app.state.retriever_service,
            gatekeeper=Gatekeeper,
            cache=global_cache
        )
        app.state.ingest_use_case = IngestUseCase(vector_store=app.state.vector_store)
        
        # 6. MCP is self-contained in FastMCP
        
        # 7. Auto-Ingest
        from app.auto_ingest import run_auto_ingest
        await run_auto_ingest(app.state.vector_store, app.state.retriever_service)
        
        # 8. Start Telegram Bridge (Background Task)
        from app.domain.services.telegram_worker import TelegramBridgeWorker
        app.state.tg_worker = TelegramBridgeWorker(app.state.chat_use_case, sio=sio)

        asyncio.create_task(app.state.tg_worker.start())
        
        logger.info("✅ Infrastructure initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize infrastructure: {e}")


    yield
    # Cleanup
    if hasattr(app.state, 'tg_worker'):
        app.state.tg_worker.stop()
    logger.info("🛑 Zyrabit SLM API Shutting down...")

app = FastAPI(title=PROJECT_NAME, version="1.7.5", lifespan=lifespan)

# Mount Socket.io
app.mount("/socket.io", socket_app)

@sio.event
async def connect(sid, environ):
    logger.info(f"🔗 Socket Connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"❌ Socket Disconnected: {sid}")

@sio.event
async def chat_message(sid, data):
    """
    Real-Time Chat Bridge: Directly calls the RAG Brain.
    """
    if not _global_app or not hasattr(_global_app.state, 'chat_use_case'):
        await sio.emit("chat_response", {"response": "System initializing..."}, to=sid)
        return

    text = data.get("text", "")
    msg_id = data.get("client_msg_id")
    
    logger.info(f"💬 Socket RAG Query from {sid}: {text[:30]}...")
    
    try:
        # Execute the EXACT SAME use case as the REST API
        result = await _global_app.state.chat_use_case.execute(text=text, client_msg_id=msg_id)
        await sio.emit("chat_response", result, to=sid)
    except Exception as e:
        logger.error(f"❌ Socket RAG Error: {e}")
        await sio.emit("chat_response", {"response": "I encountered an error processing your request."}, to=sid)

# Middleware
from app.infrastructure.shared.config import ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware, 
    allow_origins=ALLOWED_ORIGINS, 
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
