import re
import logging

logger = logging.getLogger("uvicorn.error")

# Spam/off-topic patterns that trigger reject_query
REJECT_PATTERNS = [
    r"\bviagra\b", r"\bcasino\b", r"\bcrypto\s*scam\b",
    r"comprar\s+barato\s+ahora", r"click\s+here\s+now",
]

# Keywords that suggest a RAG search is appropriate
RAG_KEYWORDS = [
    "zyrabit", "architecture", "security", "slm", "rag", "chromadb", 
    "ollama", "docker", "pyme", "n8n", "automat", "zapier",
    "resum", "documento", "pdf", "texto", "archivo", "one pager"
]

class Gatekeeper:
    """
    Sovereign Gatekeeper Service.
    Responsible for routing decisions and query validation.
    """
    
    @staticmethod
    def get_routing_decision(text: str) -> str:
        """
        Analyzes the text and returns a routing decision:
        - search_rag_database
        - direct_SLM_answer
        - reject_query
        """
        text_lower = text.lower()
        
        # 1. Reject spam/off-topic
        for pattern in REJECT_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning("Gatekeeper intercepted spam/off-topic content: %s", pattern)
                return "reject_query"
        
        # 2. Check for RAG keywords
        if any(k in text_lower for k in RAG_KEYWORDS):
            return "search_rag_database"
            
        # 3. Default to direct SLM
        return "direct_SLM_answer"
