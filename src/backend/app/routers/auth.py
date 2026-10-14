"""Auth / Connect flows for Work + MCP (two independent, per-session connects).

Mock mode: connecting immediately marks the session connected (the mock upstream accepts any
token) so the full app is usable with no tenant. Live mode: PKCE authorize in the browser, then
a server-to-server token exchange routed through APIM `/imanage/oauth/token`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ..config import Settings
from ..deps import SESSION_COOKIE, ensure_session, get_session, settings_dep

router = APIRouter()


@router.get("/status")
def status(request: Request) -> dict:
    session = get_session(request)
    return {
        "work": bool(session and session.work_token),
        "mcp": bool(session and session.mcp_token),
    }


def _start(source: str, request: Request, settings: Settings):
    if settings.imanage_backend_mode == "mock":
        # No real IdP in mock mode — mark connected and bounce back to the SPA.
        redirect = RedirectResponse(url="/ui/")
        session = ensure_session(request, redirect)
        if source == "work":
            session.work_token = "mock-work-token"
        else:
            session.mcp_token = "mock-mcp-token"
        return redirect
    # Live mode: redirect the browser to the iManage authorize endpoint (PKCE).
    auth_url = settings.work_auth_url if source == "work" else settings.mcp_auth_url
    client_id = settings.work_client_id if source == "work" else settings.mcp_client_id
    redirect_uri = f"{settings.oauth_redirect_base}/api/auth/{source}/callback"
    url = (
        f"{auth_url}?response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}&scope=openid"
    )
    redirect = RedirectResponse(url=url)
    ensure_session(request, redirect)
    return redirect


@router.get("/work/start")
def work_start(request: Request, settings: Settings = Depends(settings_dep)):
    return _start("work", request, settings)


@router.get("/mcp/start")
def mcp_start(request: Request, settings: Settings = Depends(settings_dep)):
    return _start("mcp", request, settings)


@router.get("/work/callback")
def work_callback(request: Request, code: str = "", settings: Settings = Depends(settings_dep)):
    return _callback("work", request, code, settings)


@router.get("/mcp/callback")
def mcp_callback(request: Request, code: str = "", settings: Settings = Depends(settings_dep)):
    return _callback("mcp", request, code, settings)


def _callback(source: str, request: Request, code: str, settings: Settings):
    redirect = RedirectResponse(url="/ui/")
    session = ensure_session(request, redirect)
    # Live token exchange goes through APIM; omitted detail here is completed in Epic 7.
    # For now store a marker so the session reflects a completed connect.
    token = f"exchanged-{source}-token"
    if source == "work":
        session.work_token = token
    else:
        session.mcp_token = token
    return redirect


@router.post("/logout")
def logout(request: Request) -> JSONResponse:
    from ..sessions import store

    store.clear(request.cookies.get(SESSION_COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE)
    return resp
