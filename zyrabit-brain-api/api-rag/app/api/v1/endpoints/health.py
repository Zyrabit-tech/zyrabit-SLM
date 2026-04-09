from fastapi import APIRouter
import os
import logging
from ....main import get_inference_adapter, get_vector_store_adapter, MODEL_NAME

logger = logging.getLogger("uvicorn.error")

router = APIRouter()

@router.get("/health", tags=["Monitoring"])
def health_check():
    adapter = get_inference_adapter()
    db_adapter = get_vector_store_adapter()
    
    inf_health = adapter.health()
    db_health = db_adapter.heartbeat()
    
    return {
        "status": "ok" if inf_health["ok"] and db_health else "degraded",
        "slm": "online" if inf_health["ok"] else "offline",
        "db": "online" if db_health else "offline",
        "model": MODEL_NAME,
        "details": inf_health
    }
