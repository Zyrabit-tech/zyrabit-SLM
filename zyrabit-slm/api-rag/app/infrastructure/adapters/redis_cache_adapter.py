"""
Redis Cache Adapter — Optional Redis-backed CachePort implementation.

Used for horizontal scaling where multiple API replicas share the same
idempotency cache. Auto-selected if REDIS_URL environment variable is set.
Falls back gracefully if the redis package is not installed.
"""
import json
import logging
from typing import Optional
from app.domain.ports.cache_port import CachePort

logger = logging.getLogger("zyrabit.cache")


class RedisCacheAdapter(CachePort):
    """
    Redis implementation of the CachePort.
    Imports redis dynamically so it remains an optional dependency.
    """

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        try:
            import redis
            self.client = redis.Redis.from_url(redis_url, decode_responses=True)
            logger.info("📡 RedisCacheAdapter initialized successfully.")
        except ImportError:
            logger.error("❌ Redis package not found. Run 'pip install redis' to use Redis cache.")
            raise RuntimeError("Redis package not installed")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise

    def get(self, key: str) -> Optional[dict]:
        try:
            val = self.client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"⚠️ Redis GET error for key={key}: {e}")
        return None

    def set(self, key: str, value: dict, ttl_seconds: int = 3600) -> None:
        try:
            self.client.setex(key, ttl_seconds, json.dumps(value))
        except Exception as e:
            logger.warning(f"⚠️ Redis SET error for key={key}: {e}")

    def delete(self, key: str) -> None:
        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning(f"⚠️ Redis DELETE error for key={key}: {e}")
