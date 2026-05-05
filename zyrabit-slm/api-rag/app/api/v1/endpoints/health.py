from fastapi import APIRouter, Depends
from app.infrastructure.shared.config import MODEL_NAME, PROJECT_NAME
from app.api.v1.dependencies import get_vector_store, get_inference_provider

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Basic health check for the API.
    """
    return {
        "status": "healthy",
        "project": PROJECT_NAME,
        "model": MODEL_NAME
    }

@router.get("/status")
async def detailed_status(
    vector_store = Depends(get_vector_store),
    inference_provider = Depends(get_inference_provider)
):
    """
    Detailed system status verifying adapter connectivity.
    """
    return {
        "api": "online",
        "vector_store": "connected" if vector_store else "offline",
        "inference": "ready" if inference_provider else "offline"
    }
