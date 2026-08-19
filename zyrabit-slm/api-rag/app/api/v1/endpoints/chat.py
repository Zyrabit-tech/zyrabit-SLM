from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.api.v1.dependencies import get_node_service

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
