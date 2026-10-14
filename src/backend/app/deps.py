"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Request, Response

from .config import Settings, get_settings
from .imanage_client import ImanageClient
from .sessions import Session, store

SESSION_COOKIE = "imanage_sid"


def settings_dep() -> Settings:
    return get_settings()


def client_dep() -> ImanageClient:
    return ImanageClient(get_settings())


def get_session(request: Request) -> Session | None:
    return store.get(request.cookies.get(SESSION_COOKIE))


def ensure_session(request: Request, response: Response) -> Session:
    sid = request.cookies.get(SESSION_COOKIE)
    sid, session = store.get_or_create(sid)
    response.set_cookie(
        SESSION_COOKIE, sid, httponly=True, samesite="lax", secure=False
    )
    return session
