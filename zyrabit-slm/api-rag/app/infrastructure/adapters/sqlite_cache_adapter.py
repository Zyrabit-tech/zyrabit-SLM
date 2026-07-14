"""
SQLite Cache Adapter — Persistent CachePort implementation.

Uses the existing SovereignStateManager SQLite database to store
idempotency cache entries. This ensures cache survives container restarts
without requiring any additional infrastructure.

Table schema (auto-created on first use):
  response_cache (key TEXT PK, value_json TEXT, expires_at REAL)
"""
import json
import logging
import sqlite3
import time
from typing import Optional

from app.domain.ports.cache_port import CachePort
from app.infrastructure.shared.state_tracker import SovereignStateManager

logger = logging.getLogger("zyrabit.cache")

_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS response_cache (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        expires_at REAL NOT NULL
    )
"""

_CREATE_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS idx_cache_expires
    ON response_cache(expires_at)
"""


class SqliteCacheAdapter(CachePort):
    """
    Persistent LRU-style cache backed by the Sovereign SQLite database.
    TTL is enforced on read: expired entries are lazily deleted.
    """

    def __init__(self) -> None:
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            with sqlite3.connect(SovereignStateManager.DB_PATH) as conn:
                conn.execute(_CREATE_TABLE_SQL)
                conn.execute(_CREATE_INDEX_SQL)
        except Exception as e:
            logger.error(f"❌ SqliteCacheAdapter: Failed to create table: {e}")

    def get(self, key: str) -> Optional[dict]:
        try:
            with sqlite3.connect(SovereignStateManager.DB_PATH) as conn:
                cursor = conn.execute(
                    "SELECT value_json, expires_at FROM response_cache WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                if not row:
                    return None
                value_json, expires_at = row
                if time.time() > expires_at:
                    # Lazy expiry: clean up and return None
                    conn.execute("DELETE FROM response_cache WHERE key = ?", (key,))
                    return None
                return json.loads(value_json)
        except Exception as e:
            logger.warning(f"⚠️ Cache GET error for key={key}: {e}")
            return None

    def set(self, key: str, value: dict, ttl_seconds: int = 3600) -> None:
        try:
            value_json = json.dumps(value)
            expires_at = time.time() + ttl_seconds
            with sqlite3.connect(SovereignStateManager.DB_PATH) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO response_cache (key, value_json, expires_at) VALUES (?, ?, ?)",
                    (key, value_json, expires_at)
                )
        except Exception as e:
            logger.warning(f"⚠️ Cache SET error for key={key}: {e}")

    def delete(self, key: str) -> None:
        try:
            with sqlite3.connect(SovereignStateManager.DB_PATH) as conn:
                conn.execute("DELETE FROM response_cache WHERE key = ?", (key,))
        except Exception as e:
            logger.warning(f"⚠️ Cache DELETE error for key={key}: {e}")
