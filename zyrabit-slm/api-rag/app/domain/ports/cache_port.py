"""
CachePort — Hexagonal port for idempotency cache.

The cache is used by ChatUseCase to avoid processing duplicate requests
(identified by client_msg_id). The port is backend-agnostic:
- SqliteCacheAdapter: persistent, works in single-instance deployments
- RedisCacheAdapter: optional, for horizontal scaling (set REDIS_URL env var)
"""
from abc import ABC, abstractmethod
from typing import Optional


class CachePort(ABC):
    """Abstract cache port. All adapters must implement these 3 methods."""

    @abstractmethod
    def get(self, key: str) -> Optional[dict]:
        """Retrieve a cached response dict by key. Returns None if not found or expired."""
        ...

    @abstractmethod
    def set(self, key: str, value: dict, ttl_seconds: int = 3600) -> None:
        """Store a response dict with an optional TTL (default 1 hour)."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove a cached entry by key."""
        ...
