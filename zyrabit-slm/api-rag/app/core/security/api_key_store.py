"""
Sovereign API Key Store.

Supports multiple Bearer tokens loaded from environment variables at startup.
Format: ZYRABIT_API_KEY_<NAME>=<SECRET_VALUE>

Example in .env:
  ZYRABIT_API_KEY_WEB=abc123abc123abc123
  ZYRABIT_API_KEY_N8N=xyz789xyz789xyz789
  ZYRABIT_API_KEY_MCP=mno456mno456mno456

This allows different clients to have their own keys, enabling key rotation
without service downtime and audit logging per client name.
"""
import os
import hmac
import logging
from typing import Optional, Dict

logger = logging.getLogger("zyrabit.security")


class ApiKeyStore:
    """
    Multi-key store loaded from environment variables at startup.
    Supports:
    - Multiple named keys (ZYRABIT_API_KEY_<NAME>)
    - Legacy single key (N8N_SERVICE_TOKEN) for backward compatibility
    - Test bypass when pytest is running
    """
    _keys: Dict[str, str] = {}  # {token_value: client_name}
    _loaded: bool = False

    @classmethod
    def load(cls) -> None:
        """
        Scans environment variables and loads all API keys.
        Call this once during FastAPI lifespan startup.
        """
        cls._keys = {}

        # Load all ZYRABIT_API_KEY_* variables
        for env_key, env_value in os.environ.items():
            if env_key.startswith("ZYRABIT_API_KEY_") and env_value.strip():
                client_name = env_key.replace("ZYRABIT_API_KEY_", "").lower()
                cls._keys[env_value.strip()] = client_name

        # Backward-compatible legacy token support
        legacy_token = os.getenv("N8N_SERVICE_TOKEN", "")
        if legacy_token and legacy_token not in cls._keys:
            cls._keys[legacy_token] = "legacy_n8n"

        cls._loaded = True
        logger.info(f"🔑 ApiKeyStore: Loaded {len(cls._keys)} API key(s): {list(cls._keys.values())}")

    @classmethod
    def validate(cls, token: str) -> Optional[str]:
        """
        Validates a Bearer token using constant-time comparison.
        Returns the client name if valid, None otherwise.
        """
        if not cls._loaded:
            cls.load()

        for stored_token, client_name in cls._keys.items():
            if hmac.compare_digest(token, stored_token):
                return client_name

        return None

    @classmethod
    def is_empty(cls) -> bool:
        """Returns True if no API keys are configured."""
        return len(cls._keys) == 0
