from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.v1.dependencies import get_chat_use_case
from app.domain.use_cases.chat_use_case import ChatUseCase

router = APIRouter()

class WebhookData(BaseModel):
    event: str
    payload: dict

@router.post("/webhook")
async def handle_webhook(
    data: WebhookData,
    chat_use_case: ChatUseCase = Depends(get_chat_use_case)
):
    """
    Handle external integrations (like n8n) using the ChatUseCase.
    """
    try:
        # Example: if event is a question, process it
        if data.event == "user_query":
            text = data.payload.get("text", "")
            result = await chat_use_case.execute(text=text)
            return {"status": "processed", "result": result}
        
        return {"status": "received", "event": data.event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
