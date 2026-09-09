from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.api.v1.dependencies import get_node_service, get_inference_provider
from app.domain.services.structured_extraction_service import StructuredExtractionService

router = APIRouter()

class ChatQuery(BaseModel):
    text: str
    client_msg_id: Optional[str] = None
    history: Optional[list] = []
    provider: Optional[str] = None
    session_id: Optional[str] = None
    document_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    metadata: Optional[dict] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_router(
    query: ChatQuery, 
    node_service = Depends(get_node_service)
):
    """
    Primary chat endpoint. Injects ChatUseCase via FastAPI Depends.
    """
    try:
        result = await node_service.query(query.text, query.session_id or query.client_msg_id or "default", query.document_id)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ExtractionQuery(BaseModel):
    text: str
    schema_definition: Dict[str, Any]
    instructions: Optional[str] = None
    model: Optional[str] = None

class ExtractionResponse(BaseModel):
    data: Dict[str, Any]
    valid: bool
    errors: List[str] = []
    raw_response: str
    model: str

@router.post("/extract", response_model=ExtractionResponse)
async def extract_structured_data(
    query: ExtractionQuery,
    inference_provider = Depends(get_inference_provider)
):
    """
    Structured JSON extraction endpoint.
    Extracts structured schema-conforming entities from unstructured input text.
    """
    if not inference_provider:
        raise HTTPException(status_code=503, detail="Inference provider is offline")
    service = StructuredExtractionService(inference_provider)
    result = await service.extract(
        text=query.text,
        schema=query.schema_definition,
        instructions=query.instructions,
        model=query.model
    )
    return ExtractionResponse(**result)

