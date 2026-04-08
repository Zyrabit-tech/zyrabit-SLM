from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import logging
from ....domain.services.gatekeeper import Gatekeeper
from ....domain.use_cases import ChatUseCase
from .... import services # Still temporarily needed for some helpers

logger = logging.getLogger("uvicorn.error")

router = APIRouter()

class ChatQuery(BaseModel):
    text: str

class ChatResponse(BaseModel):
    response: str
    metadata: Optional[dict] = None

# We'll use a factory or direct injection in main.py, 
# for now we'll assume the app state or a dependency provider handles the logic.

@router.post("/chat", response_model=ChatResponse)
async def chat_router(query: ChatQuery, request_id: str = Depends(lambda: str(uuid.uuid4()))):
    # 1. Gatekeeper Decision
    decision = Gatekeeper.get_routing_decision(query.text)
    
    if decision == "reject_query":
        raise HTTPException(
            status_code=400, 
            detail="Query out of scope. Please focus on Zyrabit SLM, architecture, or infrastructure topics."
        )

    # Note: Dependency injection for ChatUseCase should be handled by FastAPI
    # This is a simplified version for the refactor.
    from ....main import get_chat_use_case, MODEL_NAME
    
    chat_use_case = get_chat_use_case()
    
    if decision == "search_rag_database":
        response, hits, latency = chat_use_case.execute_rag(query.text, MODEL_NAME)
        return ChatResponse(response=response, metadata={"hits": hits, "latency": latency, "decision": decision})
    else:
        response, latency = chat_use_case.execute_direct_chat(query.text, MODEL_NAME)
        return ChatResponse(response=response, metadata={"hits": 0, "latency": latency, "decision": decision})
