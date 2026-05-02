import re
from typing import Tuple, Dict, List

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
            
        # Mask IPs
        ips = cls.IP_PATTERN.findall(text)
        if ips:
            entities["ip"].extend(ips)
            text = cls.IP_PATTERN.sub("[IP_MASKED]", text)
            
        # Mask Credit Cards
        cards = cls.CREDIT_CARD_PATTERN.findall(text)
        if cards:
            entities["credit_card"].extend(cards)
            text = cls.CREDIT_CARD_PATTERN.sub("[CARD_MASKED]", text)
            
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
        Determines the routing path: 'rag', 'direct', or 'reject'.
        """
        if not cls.is_in_scope(text):
            return "reject"
            
        # Simple heuristic: if query is about documents or retrieval, use RAG
        rag_keywords = [
            "document", "source", "context", "search", "know about", 
            "purpose", "what is", "how does", "tell me about", "info"
        ]
        if any(kw in text.lower() for kw in rag_keywords):
            return "rag"
            
        return "direct"
