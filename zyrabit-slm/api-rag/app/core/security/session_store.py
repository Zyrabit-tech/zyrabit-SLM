"""Server-side browser sessions. The service API key never leaves this process."""

from __future__ import annotations

import secrets
import time


class SessionStore:
    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}

    def create(self, client: str, ttl_seconds: int) -> tuple[str, str]:
        session_id = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        self._rows[session_id] = {
            "client": client,
            "csrf": csrf,
            "expires_at": time.time() + ttl_seconds,
        }
        return session_id, csrf

    def read(self, session_id: str) -> dict | None:
        row = self._rows.get(session_id)
        if row is None:
            return None
        if row["expires_at"] <= time.time():
            self._rows.pop(session_id, None)
            return None
        return row

    def delete(self, session_id: str) -> None:
        self._rows.pop(session_id, None)
