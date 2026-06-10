from typing import List, Dict, Any
from app.domain.ports.memory_port import ConversationMemoryPort

class SlidingWindowMemoryAdapter(ConversationMemoryPort):
    """
    Sovereign Memory Adapter: Implements a sliding window memory strategy
    limiting the active conversation history context to the last 4 turns.
    """
    def get_context_window(self, history: List[Dict[str, Any]], max_turns: int = 4) -> List[Dict[str, Any]]:
        if not history:
            return []
        
        # A "turn" consists of a user message and the corresponding assistant response (2 messages).
        # So max_turns = 4 means at most 8 messages.
        max_messages = max_turns * 2
        return history[-max_messages:]
