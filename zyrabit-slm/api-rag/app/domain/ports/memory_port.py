from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ConversationMemoryPort(ABC):
    """
    Contract for managing conversation context windows.
    """
    @abstractmethod
    def get_context_window(self, history: List[Dict[str, Any]], max_turns: int = 4) -> List[Dict[str, Any]]:
        """
        Trims or summarizes history to avoid context window collapse.
        Returns: A list of messages fitting the current context budget.
        """
        pass
