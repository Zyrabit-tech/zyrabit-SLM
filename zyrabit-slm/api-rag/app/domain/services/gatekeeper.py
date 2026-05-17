import logging
from typing import Tuple, Dict, Any
from app.infrastructure.shared.metrics import SECURITY_HITS_TOTAL
from app.core.security import pii_pipeline

logger = logging.getLogger("zyrabit.security")

class Gatekeeper:
    """
    Sovereign Shield V5.2: Orchestrates Security Policies.
    Follows SRP by delegating low-level masking to the pii_pipeline.
    """
    
    # Scope Keywords (Policy-level configuration)
    SCOPE_KEYWORDS = ["zyrabit", "slm", "architecture", "infrastructure", "docker", "mcp", "ollama", "rag"]

    @classmethod
    def mask_pii(cls, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Policy: Mask all PII before processing.
        Delegates execution to the specialized pii_pipeline.
        """
        result = pii_pipeline.anonymize_text(text)
        
        # Metrics orchestration
        for placeholder in result.token_map:
            # Extract label from placeholder, e.g., <USER_EMAIL_1> -> email
            try:
                label = placeholder.split('_')[1].lower()
                SECURITY_HITS_TOTAL.labels(entity_type=label, action="masked").inc()
            except (IndexError, AttributeError):
                continue
            
        return result.sanitized_text, result.token_map

    @classmethod
    def is_in_scope(cls, text: str) -> bool:
        """
        Policy: Determine if the query is within the Sovereign AI's domain.
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in cls.SCOPE_KEYWORDS)

    @classmethod
    def get_routing_decision(cls, text: str) -> str:
        """
        Policy: Decide if we need RAG or direct SLM response.
        """
        if cls.is_in_scope(text):
            return "rag"
        return "direct"
