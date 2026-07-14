import os
import logging
from typing import Optional
from app.domain.ports.cache_port import CachePort

logger = logging.getLogger("zyrabit.cache")


class DynamicCache(CachePort):
    """
    Hexagonal cache wrapper that selects the implementation dynamically at runtime.
    - If REDIS_URL env var is set: RedisCacheAdapter
    - Else: SqliteCacheAdapter (Default, persists between restarts)
    - Fallback: InMemoryCache (Used in tests or if SQLite creation fails)
    """

    def __init__(self) -> None:
        self._adapter: Optional[CachePort] = None

    def get_adapter(self) -> CachePort:
        if self._adapter is None:
            # 1. Attempt Redis Cache
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    from app.infrastructure.adapters.redis_cache_adapter import RedisCacheAdapter
                    self._adapter = RedisCacheAdapter(redis_url)
                    return self._adapter
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load Redis cache, falling back to SQLite: {e}")

            # 2. Attempt Persistent SQLite Cache
            try:
                from app.infrastructure.adapters.sqlite_cache_adapter import SqliteCacheAdapter
                self._adapter = SqliteCacheAdapter()
                return self._adapter
            except Exception as e:
                logger.warning(f"⚠️ Failed to load SQLite cache, falling back to in-memory: {e}")

            # 3. Fallback to In-Memory Cache (e.g. for testing)
            import time
            from typing import Dict, Any

            class InMemoryCache(CachePort):
                def __init__(self) -> None:
                    self._cache: Dict[str, Dict[str, Any]] = {}

                def get(self, key: str) -> Optional[dict]:
                    if key in self._cache:
                        entry = self._cache[key]
                        if time.time() - entry["timestamp"] < 3600:
                            return entry["data"]
                        else:
                            del self._cache[key]
                    return None

                def set(self, key: str, value: dict, ttl_seconds: int = 3600) -> None:
                    self._cache[key] = {
                        "data": value,
                        "timestamp": time.time()
                    }

                def delete(self, key: str) -> None:
                    self._cache.pop(key, None)

            self._adapter = InMemoryCache()

        return self._adapter

    def get(self, key: str) -> Optional[dict]:
        return self.get_adapter().get(key)

    def set(self, key: str, value: dict, ttl_seconds: int = 3600) -> None:
        self.get_adapter().set(key, value, ttl_seconds)

    def delete(self, key: str) -> None:
        self.get_adapter().delete(key)


# Global instance imported by use cases and endpoints
global_cache = DynamicCache()

