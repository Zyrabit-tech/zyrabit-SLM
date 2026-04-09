from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional
import logging
from ....infrastructure.integrations.n8n_adapter import N8nAdapter, N8nIntegrationPolicy
from ....main import get_chat_use_case, MODEL_NAME

logger = logging.getLogger("uvicorn.error")
router = APIRouter()

def get_n8n_adapter() -> N8nAdapter:
    policy = N8nIntegrationPolicy.from_env()
    chat_use_case = get_chat_use_case()
    
    def execute_automation(text: str) -> str:
        # For n8n, we perform a direct chat through the secure pipeline
        response, _ = chat_use_case.execute_direct_chat(text, MODEL_NAME)
        return response
        
    return N8nAdapter(policy=policy, execute_automation=execute_automation)

@router.post("/n8n/webhook")
async def n8n_webhook(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_zyrabit_signature: Optional[str] = Header(None)
):
    """Secure webhook for n8n automation workflows."""
    adapter = _build_n8n_adapter()
    raw_body = await request.body()
    
    try:
        adapter.authorize_request(
            authorization_header=authorization or "",
            signature_header=x_zyrabit_signature or "",
            raw_body=raw_body
        )
        
        payload = await request.json()
        return adapter.handle_payload(payload)
    except PermissionError as e:
        logger.warning(f"Unauthorized n8n request: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing n8n webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))
