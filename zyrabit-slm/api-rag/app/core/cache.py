import time
import logging
from typing import Dict, Any

logger = logging.getLogger("uvicorn.error")

# --- Idempotency Cache (In-Memory MVP) ---
PROCESSED_REQUESTS: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300 # 5 minutes

def clean_processed_cache():
    now = time.time()
    expired = [k for k, v in PROCESSED_REQUESTS.items() if now - v['time'] > CACHE_TTL]
    for k in expired:
        del PROCESSED_REQUESTS[k]

def get_cached_response(client_msg_id: str):
    clean_processed_cache()
    if client_msg_id and client_msg_id in PROCESSED_REQUESTS:
        logger.info(f"Idempotency hit: {client_msg_id}")
        return PROCESSED_REQUESTS[client_msg_id]['response']
    return None

def store_cached_response(client_msg_id: str, response_data: dict):
    if not client_msg_id:
        return
    PROCESSED_REQUESTS[client_msg_id] = {
        "response": response_data,
        "time": time.time()
    }
