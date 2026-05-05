from __future__ import annotations

import time
import logging
from typing import Tuple

from app.core.security import anonymize_text
from app.inference_factory import create_inference_provider
from app.ports.inference_port import InferenceRequest
from app.infrastructure.shared.config import MODEL_NAME

logger = logging.getLogger("zyrabit.api")

def query_secure_slm(prompt: str) -> Tuple[str, float]:
    """
    Backward-compatible service for secure SLM querying.
    Used by MCP bridge and legacy tests.
    """
    # 1. Mask PII
    result = anonymize_text(prompt)
    sanitized_prompt = result.sanitized_text
    
    # 2. Inference
    provider = create_inference_provider()
    
    start_time = time.time()
    try:
        request = InferenceRequest(
            model=MODEL_NAME,
            prompt=sanitized_prompt
        )
        response_obj = provider.generate(request)
        latency = response_obj.latency_seconds
        return response_obj.text, latency
    except Exception as e:
        logger.error(f"Error in query_secure_slm: {e}")
        return f"Error: {str(e)}", 0.0

__all__ = ["query_secure_slm"]
