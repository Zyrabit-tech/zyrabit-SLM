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
    RAG_COLLECTION, EMBEDDING_MODEL, EMBEDDING_URL, NODE_DATA_DIR, NODE_ENABLE_OCR,
    ENABLE_LEGACY_EXTENSIONS, DB_HOST, DB_PORT, MODEL_NAME
)
from app.infrastructure.shared.logger import setup_logging
from app.infrastructure.shared.state_tracker import SovereignStateManager
from app.infrastructure.shared.cache import global_cache

# Domain Layer
from app.domain.services.gatekeeper import Gatekeeper


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
        embeddings = DirectOllamaEmbeddings(model=EMBEDDING_MODEL, base_url=EMBEDDING_URL)
        
        # 2. Vector Store (Connecting to remote Chroma Server)
        import chromadb

        chroma_client = None
        for attempt in range(1, 4):
            try:
                client_candidate = chromadb.HttpClient(host=DB_HOST, port=DB_PORT)
                # Quick check to ensure the client is operational
                client_candidate.heartbeat()
                chroma_client = client_candidate
                logger.info(f"✅ Connected to ChromaDB at {DB_HOST}:{DB_PORT}")
                break
            except Exception as err:
                logger.warning(f"⚠️ Waiting for ChromaDB at {DB_HOST}:{DB_PORT} (attempt {attempt}/3): {err}")
                await asyncio.sleep(1)

        if not chroma_client:
            logger.info("ℹ️ Using EphemeralClient for ChromaDB (local/standalone mode).")
            chroma_client = chromadb.EphemeralClient()
        
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
        
        # 4. Inference Provider (Dynamic from environment)
        provider_name = os.getenv("INFERENCE_PROVIDER", "ollama")
        app.state.inference_provider = InferenceProviderFactory.create_sync_provider(provider_name)
        app.state.streaming_provider = InferenceProviderFactory.create_stream_provider(provider_name)
        
        # Evidence-first Node composition root. Domain services do not depend on
        # FastAPI, LangChain or Chroma; these adapters are assembled here only.
        from app.node.adapters import ChromaEvidenceIndex, ExistingInferenceAdapter
        from app.node.parsers import LocalDocumentParser, TesseractOcrAdapter
        from app.node.service import NodeService
        from app.node.sqlite_store import SQLiteNodeStore
        from app.node.storage import LocalSourceStore
        node_store = SQLiteNodeStore(os.path.join(NODE_DATA_DIR, "node.db"))
        app.state.node_store = node_store
        app.state.node_service = NodeService(
            metadata=node_store,
            source_store=LocalSourceStore(os.path.join(NODE_DATA_DIR, "sources")),
            parser=LocalDocumentParser(TesseractOcrAdapter() if NODE_ENABLE_OCR else None),
            inference=ExistingInferenceAdapter(app.state.inference_provider, MODEL_NAME),
            vector_index=ChromaEvidenceIndex(app.state.vector_store),
        )
        
        # 6. MCP is self-contained in FastMCP
        
        # Legacy integrations are preserved but never become an implicit runtime
        # dependency of the document node. Whisper remains available by endpoint.
        if ENABLE_LEGACY_EXTENSIONS:
            from app.domain.use_cases.chat_use_case import ChatUseCase
            from app.domain.use_cases.ingest_use_case import IngestUseCase
            from app.infrastructure.adapters.bge_reranker_adapter import BGEReRankerAdapter
            from app.infrastructure.adapters.sliding_window_memory_adapter import SlidingWindowMemoryAdapter
            from app.infrastructure.adapters.mcp_client_adapter import InternalMcpClientAdapter
            from app.auto_ingest import run_auto_ingest
            from app.domain.services.telegram_worker import TelegramBridgeWorker
            from app.domain.services.obsidian_service import ObsidianService
            app.state.chat_use_case = ChatUseCase(
                inference_provider=app.state.inference_provider, retriever_service=app.state.retriever_service,
                gatekeeper=Gatekeeper, cache=global_cache, telemetry=PrometheusTelemetryAdapter(),
                reranker=BGEReRankerAdapter(), memory_manager=SlidingWindowMemoryAdapter(),
                streaming_provider=app.state.streaming_provider, mcp_client=InternalMcpClientAdapter())
            app.state.ingest_use_case = IngestUseCase(vector_store=app.state.vector_store)
            await run_auto_ingest(app.state.vector_store, app.state.retriever_service)
            app.state.tg_worker = TelegramBridgeWorker(app.state.chat_use_case, sio=sio)
            asyncio.create_task(app.state.tg_worker.start())
            asyncio.create_task(ObsidianService.start_auto_learner_loop(app.state.inference_provider, interval_seconds=600))
        
        logger.info("✅ Infrastructure initialized successfully.")

    except Exception as e:
        logger.exception(f"❌ Failed to initialize infrastructure: {e}")


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
    if not _global_app or not hasattr(_global_app.state, 'node_service'):
        await sio.emit("chat_response", {"response": "System initializing..."}, to=sid)
        return

    text = data.get("text", "")
    msg_id = data.get("client_msg_id")
    # Use sid as thread_id so each socket session has its own persistent memory
    thread_id = data.get("thread_id", sid)

    logger.info(f"💬 Socket RAG Query from {sid}: {text[:30]}...")

    try:
        result = await _global_app.state.node_service.query(text, thread_id, data.get("document_id"))

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
from app.api.v1.endpoints import chat, health, documents, ag_ui, node
app.include_router(chat.router, prefix=API_V1_STR, tags=["Chat"], dependencies=[Depends(get_current_user)])
app.include_router(health.router, prefix=API_V1_STR, tags=["Monitoring"])
if ENABLE_LEGACY_EXTENSIONS:
    from app.api.v1.endpoints import mcp as mcp_router
    app.include_router(mcp_router.router, prefix="/mcp", tags=["MCP"])
app.include_router(documents.router, prefix=API_V1_STR, tags=["Documents"], dependencies=[Depends(get_current_user)])
if ENABLE_LEGACY_EXTENSIONS:
    from app.api.v1.endpoints import integrations
    app.include_router(integrations.router, prefix=API_V1_STR, tags=["Integrations"], dependencies=[Depends(get_current_user)])
app.include_router(ag_ui.router, prefix="/ag-ui", tags=["AG-UI"])
app.include_router(node.router, prefix=API_V1_STR, tags=["Node"], dependencies=[Depends(get_current_user)])

@app.get("/", include_in_schema=False)
async def root():
    return {"status": "Zyrabit SLM API is running."}
