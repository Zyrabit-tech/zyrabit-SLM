from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.domain.services.gatekeeper import Gatekeeper
from app.core.config import MODEL_NAME
from app.core.factories import get_chat_use_case
from app.core.cache import get_cached_response, store_cached_response

logger = logging.getLogger("uvicorn.error")
router = APIRouter()

class ChatQuery(BaseModel):
    text: str
    client_msg_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    metadata: Optional[dict] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_router(query: ChatQuery):
    # 1. Idempotency Check
    cached = get_cached_response(query.client_msg_id)
    if cached:
        return ChatResponse(**cached)

    # 2. Gatekeeper Decision
    decision = Gatekeeper.get_routing_decision(query.text)
    
    if decision == "reject_query":
        raise HTTPException(
            status_code=400, 
            detail="Query out of scope. Please focus on Zyrabit SLM, architecture, or infrastructure topics."
        )

    # 3. Execution
    try:
        chat_use_case = get_chat_use_case()
        
        if decision == "search_rag_database":
            response, hits, latency, sources = chat_use_case.execute_rag(query.text, MODEL_NAME)
            res_data = {
                "response": response, 
                "metadata": {
                    "hits": hits, 
                    "latency": latency, 
                    "decision": decision,
                    "sources": sources
                }
            }
        else:
            response, latency = chat_use_case.execute_direct_chat(query.text, MODEL_NAME)
            res_data = {
                "response": response, 
                "metadata": {"hits": 0, "latency": latency, "decision": decision}
            }
        
        # 4. Store & Return
        store_cached_response(query.client_msg_id, res_data)
        return ChatResponse(**res_data)

    except Exception as e:
        logger.error(f"REST API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
