import os
import platform
import psutil
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from app.infrastructure.shared.config import MODEL_NAME, PROJECT_NAME, SLM_URL
from app.api.v1.dependencies import get_vector_store, get_inference_provider

router = APIRouter()

# Global startup time
STARTUP_TIME = datetime.now()

def get_system_stats():
    return {
        "cpu_usage": f"{psutil.cpu_percent()}%",
        "ram_usage": f"{psutil.virtual_memory().percent}%",
        "platform": platform.system(),
        "arch": platform.machine()
    }

@router.get("/health")
async def health_check(
    request: Request,
    vector_store = Depends(get_vector_store),
    inference_provider = Depends(get_inference_provider)
):
    """
    PREMIUM Health Check: Returns ordered hard data about all systems.
    """
    # 1. System Metadata
    uptime = str(datetime.now() - STARTUP_TIME).split('.')[0]
    
    # 2. Vector DB Check
    db_status = "OFFLINE"
    doc_count = 0
    if vector_store:
        try:
            if vector_store.heartbeat():
                db_status = "ONLINE"
                # Accessing underlying chroma collection for count
                if hasattr(vector_store.vector_store, "_collection"):
                    doc_count = vector_store.vector_store._collection.count()
        except:
            pass

    # 3. SLM Engine Check
    slm_status = "OFFLINE"
    slm_metadata = {"ok": False}
    if inference_provider:
        slm_metadata = inference_provider.health()
        slm_status = "ONLINE" if slm_metadata.get("ok") else "OFFLINE"

    # 4. Mode Detection
    is_local_host = any(x in SLM_URL for x in ["host.docker.internal", "localhost", "127.0.0.1"])
    
    # Ordered Hard Data
    return {
        "status": "OPERATIONAL",
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "project": PROJECT_NAME,
            "version": os.getenv("VERSION", "0.1.0-dev"),
            "uptime": uptime,
            "system": get_system_stats()
        },
        "infrastructure": [
            {
                "id": "core-api",
                "name": "Zyrabit Core API",
                "status": "ONLINE",
                "type": "Runtime"
            },
            {
                "id": "vector-db",
                "name": "ChromaDB Memory",
                "status": db_status,
                "type": "Persistence",
                "metrics": {"documents": doc_count}
            },
            {
                "id": "slm-engine",
                "name": f"Ollama ({MODEL_NAME})",
                "status": slm_status,
                "type": "Inference",
                "mode": "Local Host (Mac)" if is_local_host else "Container",
                "details": slm_metadata
            }
        ]
    }

@router.get("/status")
async def detailed_status(
    vector_store = Depends(get_vector_store),
    inference_provider = Depends(get_inference_provider)
):
    """
    Legacy detailed status for CLI/Internal tools.
    """
    db_ok = False
    if vector_store:
        db_ok = vector_store.heartbeat()
        
    slm_ok = False
    if inference_provider:
        slm_health = inference_provider.health()
        slm_ok = slm_health.get("ok", False)

    return {
        "api": "online",
        "vector_store": "connected" if db_ok else "offline",
        "inference": "ready" if slm_ok else "offline"
    }
