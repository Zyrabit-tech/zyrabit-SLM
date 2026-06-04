from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hmac
from app.infrastructure.shared.config import N8N_SERVICE_TOKEN

security = HTTPBearer(auto_error=False)

class User:
    def __init__(self, id: int = 1, name: str = "Admin"):
        self.id = id
        self.name = name

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    if not hmac.compare_digest(token, N8N_SERVICE_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid token")
    return User(id=1, name="Admin")
