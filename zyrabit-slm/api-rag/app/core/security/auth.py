import sys
import logging
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security.api_key_store import ApiKeyStore

logger = logging.getLogger("zyrabit.security")
security = HTTPBearer(auto_error=False)


class User:
    def __init__(self, id: int = 1, name: str = "Admin", client: str = "unknown"):
        self.id = id
        self.name = name
        self.client = client  # e.g. "web", "n8n", "mcp"


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> User:
    """
    Validates Bearer token against the ApiKeyStore.
    Supports multiple named API keys (ZYRABIT_API_KEY_<NAME>).
    Falls back to test-token when running under pytest.
    """
    # Test environment bypass
    if "pytest" in sys.modules:
        if credentials and credentials.credentials == "test-token":
            return User(id=1, name="TestUser", client="test")

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated: Bearer token required")

    client_name = ApiKeyStore.validate(credentials.credentials)
    if not client_name:
        logger.warning("🚫 Auth rejected: invalid or unknown API key presented")
        raise HTTPException(status_code=401, detail="Invalid token")

    logger.debug(f"✅ Auth accepted: client='{client_name}'")
    return User(id=1, name="Admin", client=client_name)

