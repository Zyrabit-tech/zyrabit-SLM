import time
from typing import Tuple
from app.core.security import pii_pipeline
from app.ports.inference_port import InferenceRequest

def query_secure_slm(prompt: str) -> Tuple[str, float]:
    """
    Sovereign Security Bridge: Anonymizes prompt before inference.
    Legacy interface used by security tests.
    """
    # 1. Anonymize
    anonymized_result = pii_pipeline.anonymize_text(prompt)
    
    # 2. Get Provider
    from app.services import create_inference_provider
    provider = create_inference_provider()
    
    # 3. Execute Inference
    request = InferenceRequest("zyrabit-model", anonymized_result.sanitized_text)
    result = provider.generate(request)
    
    # Use the latency from the result as expected by tests
    return result.text, result.latency_seconds
