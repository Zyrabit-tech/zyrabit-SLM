import hmac
import logging
import os
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security.api_key_store import ApiKeyStore

logger = logging.getLogger("zyrabit.security")
security = HTTPBearer(auto_error=False)


class User:
    def __init__(self, id: int = 1, name: str = "Admin", client: str = "unknown"):
        self.id = id
        self.name = name
        self.client = client  # e.g. "web", "n8n", "mcp"


def user_from_bearer(token: str) -> User:
    """Validate a service credential. Callers that already hold the token use this."""
    client_name = ApiKeyStore.validate(token)
    if not client_name:
        logger.warning("🚫 Auth rejected: invalid or unknown API key presented")
        raise HTTPException(status_code=401, detail="Invalid token")
    logger.debug(f"✅ Auth accepted: client='{client_name}'")
    return User(id=1, name="Admin", client=client_name)


def _csrf_matches(request: Request, expected: str) -> bool:
    presented = request.headers.get("x-csrf-token", "")
    if not presented or not expected:
        return False
    return hmac.compare_digest(presented, expected)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> User:
    """Accept a Bearer credential or a server-side session cookie.

    Cookie authentication is for the browser. Mutable cookie requests must
    also present the matching CSRF token. Bearer requests are the CLI and
    service path and do not use the CSRF cookie.
    """
    if credentials and credentials.credentials:
        return user_from_bearer(credentials.credentials)

    store = getattr(request.app.state, "sessions", None)
    session_id = request.cookies.get("zyrabit_session") if request else None
    row = store.read(session_id) if store and session_id else None
    if not row:
        raise HTTPException(status_code=401, detail="Not authenticated: Bearer token required")

    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and not _csrf_matches(request, row["csrf"]):
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
    return User(id=1, name="Admin", client=row["client"])


def require_document_admin(user: User) -> None:
    """Single-tenant rule: authentication is not permission to delete.

    Only client names listed in ZYRABIT_ADMIN_CLIENTS may delete documents.
    The default is the explicit ``admin`` identity. This deployment does not
    claim isolation between tenants.
    """
    configured = os.getenv("ZYRABIT_ADMIN_CLIENTS", "admin")
    allowed = {name.strip().lower() for name in configured.split(",") if name.strip()}
    if user.client.lower() not in allowed:
        raise HTTPException(status_code=403, detail="Document deletion requires an administrator identity")

