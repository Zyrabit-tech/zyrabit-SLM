from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import logging
from .... import services

logger = logging.getLogger("uvicorn.error")

router = APIRouter()

DOCS_DIR = os.getenv("DOCS_DIR", "./document_source")

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
async def ingest_document(file: UploadFile = File(...)):
    """Uploads and ingests a single document."""
    os.makedirs(DOCS_DIR, exist_ok=True)
    file_path = os.path.join(DOCS_DIR, file.filename)
    
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        result = services.process_and_ingest_file(file_path)
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail="Failed to ingest document.")
            
        return result
    except Exception as e:
        logger.error(f"Failed to ingest {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during ingestion.")
