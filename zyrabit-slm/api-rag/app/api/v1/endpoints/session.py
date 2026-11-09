"""Same-origin browser session. The service credential is accepted once and discarded."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.core.security.api_key_store import ApiKeyStore
from app.core.security.auth import User, get_current_user
from app.core.security.session_store import SessionStore

router = APIRouter()

SESSION_COOKIE = "zyrabit_session"
CSRF_COOKIE = "zyrabit_csrf"


class SessionLogin(BaseModel):
    token: str = Field(min_length=1, max_length=512)


def session_store(request: Request) -> SessionStore:
    store = getattr(request.app.state, "sessions", None)
    if store is None:
        store = SessionStore()
        request.app.state.sessions = store
    return store


def session_ttl() -> int:
    raw = os.getenv("ZYRABIT_SESSION_TTL_SECONDS", "43200")
    try:
        ttl = int(raw)
    except ValueError:
        ttl = 43200
    return ttl if ttl > 0 else 43200


def cookie_flags(request: Request) -> dict:
    secure = os.getenv("ZYRABIT_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
    secure = secure or request.url.scheme == "https"
    samesite = os.getenv("ZYRABIT_COOKIE_SAMESITE", "lax").strip().lower()
    if samesite not in {"lax", "strict", "none"}:
        samesite = "lax"
    if samesite == "none" and not secure:
        samesite = "lax"
    return {"secure": secure, "samesite": samesite}


def write_session_cookies(request: Request, response: Response, session_id: str, csrf: str) -> None:
    flags = cookie_flags(request)
    ttl = session_ttl()
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=ttl,
        httponly=True,
        secure=flags["secure"],
        samesite=flags["samesite"],
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        max_age=ttl,
        httponly=False,
        secure=flags["secure"],
        samesite=flags["samesite"],
        path="/",
    )


@router.post("/session")
async def open_session(payload: SessionLogin, request: Request, response: Response):
    client = ApiKeyStore.validate(payload.token)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid token")
    session_id, csrf = session_store(request).create(client, session_ttl())
    write_session_cookies(request, response, session_id, csrf)
    return {"client": client, "expires_in": session_ttl()}


@router.get("/session")
async def read_session(current_user: User = Depends(get_current_user)):
    return {"client": current_user.client}


@router.delete("/session")
async def close_session(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
):
    del current_user
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        session_store(request).delete(session_id)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"status": "closed"}
