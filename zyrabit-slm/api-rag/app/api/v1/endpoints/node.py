"""Public API for the evidence-first local node."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_node_service

router = APIRouter()


class QueryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    session_id: str = Field(default="default", min_length=1, max_length=128)
    document_id: str | None = None


@router.post("/sources/import", status_code=202)
async def import_source(file: UploadFile = File(...), service=Depends(get_node_service)):
    if not file.filename:
        raise HTTPException(status_code=422, detail="A filename is required")
    suffix = Path(file.filename).suffix
    fd, staged = tempfile.mkstemp(prefix="zyrabit-import-", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as output:
            while chunk := await file.read(1024 * 1024): output.write(chunk)
        return await service.import_file(Path(file.filename).name, staged)
    finally:
        if os.path.exists(staged): os.unlink(staged)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, service=Depends(get_node_service)):
    result = service.job(job_id)
    if not result: raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.get("/documents/{document_id}")
async def get_document(document_id: str, service=Depends(get_node_service)):
    result = service.document(document_id)
    if not result: raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.post("/documents/{document_id}/reindex", status_code=202)
async def reindex_document(document_id: str, service=Depends(get_node_service)):
    try:
        return await service.reindex_document(document_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get("/node/documents")
async def list_node_documents(service=Depends(get_node_service)):
    return {"documents": service.documents()}


@router.post("/query")
async def query_node(payload: QueryRequest, service=Depends(get_node_service)):
    return await service.query(payload.text, payload.session_id, payload.document_id)


@router.get("/health/capabilities")
async def capabilities(service=Depends(get_node_service)):
    return {"capabilities": service.capabilities()}


@router.delete("/sessions/{session_id}", status_code=204)
async def clear_session(session_id: str, service=Depends(get_node_service)):
    service.clear_session(session_id)
