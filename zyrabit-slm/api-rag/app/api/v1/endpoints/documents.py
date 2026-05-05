from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
import os
import logging
from app.infrastructure.shared.config import DOCS_DIR
from app.api.v1.dependencies import get_ingest_use_case
from app.domain.use_cases.ingest_use_case import IngestUseCase

logger = logging.getLogger("uvicorn.error")
router = APIRouter()

@router.get("/documents")
async def list_documents():
    """Lists all files in the document source directory."""
    if not os.path.exists(DOCS_DIR):
        return {"documents": []}
    
    files = []
    for f in os.listdir(DOCS_DIR):
        if os.path.isfile(os.path.join(DOCS_DIR, f)):
            stats = os.stat(os.path.join(DOCS_DIR, f))
            files.append({
                "filename": f,
                "size_bytes": stats.st_size
            })
    return {"documents": files}

@router.post("/ingest")
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    ingest_use_case: IngestUseCase = Depends(get_ingest_use_case)
):
    """
    Uploads and schedules ingestion in the background.
    Returns 202 Accepted immediately.
    """
    os.makedirs(DOCS_DIR, exist_ok=True)
    file_path = os.path.join(DOCS_DIR, file.filename)
    
    try:
        # 1. Save file locally
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # 2. Schedule background processing
        # We don't await here, we return immediately
        background_tasks.add_task(ingest_use_case.execute, file_path)
        
        return {
            "status": "accepted", 
            "message": f"File {file.filename} uploaded and scheduled for ingestion.",
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"Failed to initiate ingestion for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")
