import re
from typing import Tuple, Dict, List
from app.infrastructure.shared.metrics import SECURITY_HITS_TOTAL

class Gatekeeper:
    """
    Sovereign Shield: Protects the system from PII leaks and out-of-scope queries.
    Uses optimized Regex for high-performance masking.
    """
    
    # Optimized Patterns
    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    IP_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
    CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
    
    # Scope Keywords (Fast screening)
    SCOPE_KEYWORDS = ["zyrabit", "slm", "architecture", "infrastructure", "docker", "mcp", "ollama", "rag"]

    @classmethod
    def mask_pii(cls, text: str) -> Tuple[str, Dict[str, List[str]]]:
        """
        Scans and masks PII in text. Returns (masked_text, entities_found).
        """
        entities = {"email": [], "ip": [], "credit_card": []}
        
        # Mask Emails
        emails = cls.EMAIL_PATTERN.findall(text)
        if emails:
            entities["email"].extend(emails)
            text = cls.EMAIL_PATTERN.sub("[EMAIL_MASKED]", text)
            SECURITY_HITS_TOTAL.labels(entity_type="email", action="masked").inc(len(emails))
            
        # Mask IPs
        ips = cls.IP_PATTERN.findall(text)
        if ips:
            entities["ip"].extend(ips)
            text = cls.IP_PATTERN.sub("[IP_MASKED]", text)
            SECURITY_HITS_TOTAL.labels(entity_type="ip", action="masked").inc(len(ips))
            
        # Mask Credit Cards
        cards = cls.CREDIT_CARD_PATTERN.findall(text)
        if cards:
            entities["credit_card"].extend(cards)
            text = cls.CREDIT_CARD_PATTERN.sub("[CARD_MASKED]", text)
            SECURITY_HITS_TOTAL.labels(entity_type="credit_card", action="masked").inc(len(cards))
            
        return text, entities

    @classmethod
    def is_in_scope(cls, text: str) -> bool:
        """
        Checks if the query is relevant to Zyrabit or general tech infrastructure.
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in cls.SCOPE_KEYWORDS)

    @classmethod
    def get_routing_decision(cls, text: str) -> str:
        """
        Determines the routing path: 'rag' (with docs) or 'direct' (general knowledge).
        We no longer 'reject' unless it's a security violation.
        """
        # If it has scope keywords, we definitely want RAG
        if cls.is_in_scope(text):
            return "rag"
            
        # For everything else, let the SLM handle it directly
        return "direct"
