import asyncio
import os
import logging
# pyrefly: ignore [missing-import]
import socketio
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Depends
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
from app.domain.services.command_router import CommandRouter


# Infrastructure Adapters
from app.infrastructure.persistence.chroma_adapter import ChromaAdapter, DirectOllamaEmbeddings
from app.infrastructure.inference.factory import InferenceProviderFactory
from app.infrastructure.telemetry.prometheus_telemetry_adapter import PrometheusTelemetryAdapter
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

    # 0b. Load API Key Store (multi-key auth)
    from app.core.security.api_key_store import ApiKeyStore
    ApiKeyStore.load()


    logger.info("🚀 Zyrabit SLM API Starting...")
    
    if os.getenv("TESTING") == "true":
        logger.info("🧪 Test Mode: Skipping heavy infrastructure initialization.")
        yield
        return

    try:
        # 1. Direct Embeddings
        embeddings = DirectOllamaEmbeddings(model=EMBEDDING_MODEL, base_url=SLM_URL)
        
        # 2. Vector Store (Connecting to remote Chroma Server with retry loop)
        import chromadb
        from chromadb.config import Settings
        import time

        chroma_settings = Settings(anonymized_telemetry=False)
        chroma_client = None
        for attempt in range(1, 6):
            try:
                client = chromadb.HttpClient(host=DB_HOST, port=DB_PORT, settings=chroma_settings)
                client.heartbeat()
                chroma_client = client
                logger.info(f"✅ Connected to ChromaDB at {DB_HOST}:{DB_PORT}")
                break
            except Exception as conn_err:
                logger.warning(f"⚠️ Waiting for ChromaDB at {DB_HOST}:{DB_PORT} (attempt {attempt}/5): {conn_err}")
                time.sleep(2)
        
        if not chroma_client:
            try:
                chroma_client = chromadb.HttpClient(host=DB_HOST, port=DB_PORT, settings=chroma_settings)
            except Exception as client_err:
                logger.error(f"⚠️ Could not initialize HttpClient for ChromaDB: {client_err}. Falling back to EphemeralClient.")
                chroma_client = chromadb.EphemeralClient(settings=chroma_settings)

        lc_chroma = Chroma(
            client=chroma_client,
            collection_name=RAG_COLLECTION,
            embedding_function=embeddings
        )
        app.state.vector_store = ChromaAdapter(lc_chroma)
        
        # 3. Hybrid Retriever
        app.state.retriever_service = HybridRetrieverService(lc_chroma)
        
        # Initialize BM25 on startup with existing documents from Vector DB
        try:
            from langchain_core.documents import Document
            db_docs = lc_chroma.get()
            if db_docs and db_docs.get("documents"):
                documents = []
                for text, metadata in zip(db_docs["documents"], db_docs["metadatas"]):
                    documents.append(Document(page_content=text, metadata=metadata))
                if documents:
                    app.state.retriever_service.update_bm25_index(documents)
                    logger.info(f"📈 Loaded {len(documents)} existing documents into BM25 index on startup.")
        except Exception as e:
            logger.error(f"⚠️ Failed to load existing documents for BM25: {e}")
        
        # 4. Inference Provider (Dynamic from INFERENCE_PROVIDER env)
        provider_env = os.getenv("INFERENCE_PROVIDER", "ollama")
        app.state.inference_provider = InferenceProviderFactory.create_sync_provider(provider_env)
        app.state.streaming_provider = InferenceProviderFactory.create_stream_provider(provider_env)
        
        # 5. Use Cases (Singletons for the session)
        from app.infrastructure.adapters.bge_reranker_adapter import BGEReRankerAdapter
        from app.infrastructure.adapters.sliding_window_memory_adapter import SlidingWindowMemoryAdapter
        from app.infrastructure.adapters.mcp_client_adapter import InternalMcpClientAdapter
        
        reranker = BGEReRankerAdapter()
        memory_manager = SlidingWindowMemoryAdapter()
        mcp_client = InternalMcpClientAdapter()
        
        telemetry_adapter = PrometheusTelemetryAdapter()
        app.state.chat_use_case = ChatUseCase(
            inference_provider=app.state.inference_provider,
            retriever_service=app.state.retriever_service,
            gatekeeper=Gatekeeper,
            cache=global_cache,
            telemetry=telemetry_adapter,
            reranker=reranker,
            memory_manager=memory_manager,
            streaming_provider=app.state.streaming_provider,
            mcp_client=mcp_client
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
        
        # 9. Start Obsidian AutoLearner Background Task (Every 10 minutes)
        from app.domain.services.obsidian_service import ObsidianService
        asyncio.create_task(ObsidianService.start_auto_learner_loop(app.state.inference_provider, interval_seconds=600))
        
        logger.info("✅ Infrastructure initialized successfully.")

    except Exception as e:
        logger.error(f"❌ Failed to initialize infrastructure: {e}", exc_info=True)


    yield
    # Cleanup
    if hasattr(app.state, 'tg_worker'):
        app.state.tg_worker.stop()
    logger.info("🛑 Zyrabit SLM API Shutting down...")

app = FastAPI(title=PROJECT_NAME, version="2.1.0", lifespan=lifespan)

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
    # Use sid as thread_id so each socket session has its own persistent memory
    thread_id = data.get("thread_id", sid)

    logger.info(f"💬 Socket RAG Query from {sid}: {text[:30]}...")

    try:
        # 1. COMMAND INTERCEPTION (Zero-Lag)
        command_res = await CommandRouter.handle(text, source="WEB", session_id=thread_id)
        if command_res:
            await sio.emit("chat_response", command_res, to=sid)
            return

        # 2. Recover history for this session (Sovereign Memory)
        from app.infrastructure.shared.state_tracker import SovereignStateManager
        history = SovereignStateManager.get_history(thread_id)

        # 3. RAG BRAIN EXECUTION with history context
        result = await _global_app.state.chat_use_case.execute(
            text=text,
            client_msg_id=msg_id,
            history=history,
        )

        # 4. Record TTFT via telemetry (socket path uses execute(), not stream_response())
        latency_ms = result.get("metadata", {}).get("latency_ms", 0)
        if latency_ms and hasattr(_global_app.state, 'chat_use_case'):
            _global_app.state.chat_use_case.telemetry.record_ttft(latency_ms)

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
from app.core.security import get_current_user
from app.api.v1.endpoints import chat, health, mcp as mcp_router, documents, integrations, ag_ui
app.include_router(chat.router, prefix=API_V1_STR, tags=["Chat"], dependencies=[Depends(get_current_user)])
app.include_router(health.router, prefix=API_V1_STR, tags=["Monitoring"])
app.include_router(mcp_router.router, prefix="/mcp", tags=["MCP"])
app.include_router(documents.router, prefix=API_V1_STR, tags=["Documents"], dependencies=[Depends(get_current_user)])
app.include_router(integrations.router, prefix=API_V1_STR, tags=["Integrations"], dependencies=[Depends(get_current_user)])
app.include_router(ag_ui.router, prefix="/ag-ui", tags=["AG-UI"])

@app.get("/", include_in_schema=False)
async def root():
    return {"status": "Zyrabit SLM API is running."}
