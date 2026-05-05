import time
from typing import Dict, Any, Optional

class IdempotencyCache:
    """
    KISS In-Memory Cache to prevent redundant SLM generations.
    """
    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self._ttl:
                return entry["data"]
            else:
                del self._cache[key]
        return None

    def set(self, key: str, data: Dict[str, Any]):
        self._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

    def clear(self):
        self._cache.clear()

# Global Instance (Infrastructure Shared)
global_cache = IdempotencyCache()
