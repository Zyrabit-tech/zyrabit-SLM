from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.api.v1.dependencies import get_chat_use_case
from app.domain.use_cases.chat_use_case import ChatUseCase

router = APIRouter()

class ChatQuery(BaseModel):
    text: str
    client_msg_id: Optional[str] = None
    history: Optional[list] = []

class ChatResponse(BaseModel):
    response: str
    metadata: Optional[dict] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_router(
    query: ChatQuery, 
    chat_use_case: ChatUseCase = Depends(get_chat_use_case)
):
    """
    Primary chat endpoint. Injects ChatUseCase via FastAPI Depends.
    """
    try:
        # The logic is now encapsulated in the Use Case
        result = await chat_use_case.execute(
            text=query.text, 
            client_msg_id=query.client_msg_id,
            history=query.history
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
