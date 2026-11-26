from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.api.v1.dependencies import get_node_service, get_inference_provider
from app.domain.services.structured_extraction_service import StructuredExtractionService

from app.core.security.auth import get_current_user, User

router = APIRouter()

class ChatQuery(BaseModel):
    text: str
    client_msg_id: Optional[str] = Field(None, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    history: Optional[list] = []
    provider: Optional[str] = None
    session_id: Optional[str] = Field(None, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    document_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    metadata: Optional[dict] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_router(
    query: ChatQuery, 
    node_service = Depends(get_node_service),
    current_user: User = Depends(get_current_user),
):
    """
    Primary chat endpoint. Injects ChatUseCase via FastAPI Depends.
    """
    try:
        caller_id = getattr(current_user, "client", None) or getattr(current_user, "name", None)
        result = await node_service.query(
            query.text,
            query.session_id or query.client_msg_id or "default",
            query.document_id,
            caller_id=caller_id,
        )
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
    schema_valid: bool
    errors: List[str] = []
    ungrounded_fields: List[str] = []
    raw_response: str
    model: str

@router.post("/extract", response_model=ExtractionResponse)
async def extract_structured_data(
    query: ExtractionQuery,
    inference_provider = Depends(get_inference_provider)
):
    """
    Structured JSON extraction endpoint.

    ``schema_valid`` means types/required fields match the schema only — it is
    **not** a claim that numeric or string values are factually grounded in the
    source text. See ``ungrounded_fields`` for values that do not appear literally.
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

