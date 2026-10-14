"""Fake iManage OAuth2 provider for the mock upstream.

Mirrors the two iManage OAuth surfaces the real product uses so the whole
on-behalf-of (OBO) flow can be demoed without a real iManage tenant:

  * /auth/oauth2/authorize + /auth/oauth2/token  -> Work API client (web app sign-in)
  * /mcp/oauth2/authorize  + /mcp/oauth2/token   -> MCP client (Foundry hosted agent OBO)

It implements Authorization Code + PKCE (S256) and refresh_token, plus the OAuth
discovery documents MCP clients look for. Tokens are opaque and in-memory. Going to
production is a pure config swap: point the authorize/token URLs at cloudimanage.com.

Nothing here is secure by design -- it exists only to make demos exercise the real
consent + code-exchange + token-passthrough plumbing end to end.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass, field

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

router = APIRouter(tags=["Mock OAuth"])

# Fake end user every demo token resolves to.
DEMO_USER = {"id": "jchen", "name": "Jordan Chen", "email": "jordan.chen@example.test"}


@dataclass
class _AuthCode:
    client_id: str
    redirect_uri: str
    scope: str
    code_challenge: str
    code_challenge_method: str
    created_at: float = field(default_factory=time.time)


# In-memory stores (reset on restart) -- fine for a demo upstream.
_CODES: dict[str, _AuthCode] = {}
_TOKENS: dict[str, dict] = {}


def _verify_pkce(code: _AuthCode, code_verifier: str | None) -> None:
    if not code.code_challenge:
        return  # challenge was not supplied at authorize time; nothing to verify
    if not code_verifier:
        raise HTTPException(status_code=400, detail="code_verifier required")
    if code.code_challenge_method.upper() == "S256":
        digest = hashlib.sha256(code_verifier.encode()).digest()
        computed = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    else:
        computed = code_verifier
    if not secrets.compare_digest(computed, code.code_challenge):
        raise HTTPException(status_code=400, detail="PKCE verification failed")


def _issue_tokens(scope: str) -> dict:
    access = f"mock-at-{secrets.token_urlsafe(24)}"
    refresh = f"mock-rt-{secrets.token_urlsafe(24)}"
    record = {"user": DEMO_USER, "scope": scope, "expires_at": time.time() + 3600}
    _TOKENS[access] = record
    _TOKENS[refresh] = {**record, "refresh": True}
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": refresh,
        "scope": scope,
    }


def _consent_page(surface_label: str, action_url: str, params: dict[str, str]) -> HTMLResponse:
    hidden = "".join(
        f'<input type="hidden" name="{k}" value="{v}">' for k, v in params.items() if v is not None
    )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Mock iManage sign-in</title>
<style>
 body{{font-family:Segoe UI,system-ui,sans-serif;background:#f3f2f1;margin:0;display:flex;
      min-height:100vh;align-items:center;justify-content:center}}
 .card{{background:#fff;padding:32px 36px;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.12);
      width:380px}}
 h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#605e5c;font-size:13px;margin:0 0 20px}}
 .row{{font-size:13px;color:#323130;margin:6px 0}} .row b{{color:#201f1e}}
 button{{margin-top:22px;width:100%;padding:10px;border:0;border-radius:4px;background:#0f6cbd;
      color:#fff;font-size:14px;cursor:pointer}} button:hover{{background:#115ea3}}
 .brand{{color:#0f6cbd;font-weight:600;letter-spacing:.3px}}
</style></head>
<body><form class="card" method="post" action="{action_url}">
 <div class="brand">MOCK iMANAGE</div>
 <h1>Approve access</h1>
 <p class="sub">{surface_label}</p>
 <div class="row">Signed in as <b>{DEMO_USER['name']}</b> ({DEMO_USER['email']})</div>
 <div class="row">Application: <b>{params.get('client_id','')}</b></div>
 <div class="row">Scope: <b>{params.get('scope','') or '(default)'}</b></div>
 {hidden}
 <button type="submit" name="decision" value="approve">Approve</button>
</form></body></html>"""
    return HTMLResponse(html)


def _authorize(surface_label: str, request: Request, **params) -> HTMLResponse:
    # Show a consent screen; the form posts back to the same path + /decision on whatever
    # host served this page. An absolute path keeps the correct https origin behind App
    # Service TLS termination (url_for would emit an http:// scheme and break the redirect).
    action = request.url.path.rstrip("/") + "/decision"
    return _consent_page(surface_label, action, {k: v for k, v in params.items() if v})


def _authorize_decision(
    surface: str,
    redirect_uri: str,
    scope: str,
    state: str | None,
    client_id: str,
    code_challenge: str | None,
    code_challenge_method: str | None,
    decision: str,
) -> RedirectResponse:
    if decision != "approve":
        raise HTTPException(status_code=400, detail="Access denied by user")
    code = f"mock-code-{secrets.token_urlsafe(18)}"
    _CODES[code] = _AuthCode(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope or "",
        code_challenge=code_challenge or "",
        code_challenge_method=code_challenge_method or "S256",
    )
    sep = "&" if "?" in redirect_uri else "?"
    target = f"{redirect_uri}{sep}code={code}"
    if state:
        target += f"&state={state}"
    return RedirectResponse(url=target, status_code=302)


def _token(grant_type: str, code: str | None, code_verifier: str | None, refresh_token: str | None) -> JSONResponse:
    if grant_type == "authorization_code":
        if not code or code not in _CODES:
            raise HTTPException(status_code=400, detail="invalid_grant")
        record = _CODES.pop(code)
        _verify_pkce(record, code_verifier)
        return JSONResponse(_issue_tokens(record.scope))
    if grant_type == "refresh_token":
        if not refresh_token or refresh_token not in _TOKENS:
            raise HTTPException(status_code=400, detail="invalid_grant")
        scope = _TOKENS[refresh_token].get("scope", "")
        return JSONResponse(_issue_tokens(scope))
    raise HTTPException(status_code=400, detail=f"unsupported_grant_type: {grant_type}")


# --- MCP OAuth surface (Foundry hosted agent OBO) ---------------------------------

@router.get("/mcp/oauth2/authorize", include_in_schema=False)
def mcp_authorize(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query("code"),
    scope: str = Query("imanage_search_mcp_scopes"),
    state: str | None = Query(None),
    code_challenge: str | None = Query(None),
    code_challenge_method: str | None = Query("S256"),
) -> HTMLResponse:
    return _authorize(
        "iManage MCP (document search & fetch)", request,
        client_id=client_id, redirect_uri=redirect_uri, scope=scope, state=state,
        code_challenge=code_challenge, code_challenge_method=code_challenge_method,
    )


@router.post("/mcp/oauth2/authorize/decision", name="mcp_authorize_decision", include_in_schema=False)
def mcp_authorize_decision(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(""),
    state: str | None = Form(None),
    code_challenge: str | None = Form(None),
    code_challenge_method: str | None = Form("S256"),
    decision: str = Form("approve"),
) -> RedirectResponse:
    return _authorize_decision("mcp", redirect_uri, scope, state, client_id, code_challenge, code_challenge_method, decision)


@router.post("/mcp/oauth2/token", include_in_schema=False)
def mcp_token(
    grant_type: str = Form(...),
    code: str | None = Form(None),
    code_verifier: str | None = Form(None),
    refresh_token: str | None = Form(None),
) -> JSONResponse:
    return _token(grant_type, code, code_verifier, refresh_token)


# --- Work API OAuth surface (web app sign-in) -------------------------------------

@router.get("/auth/oauth2/authorize", include_in_schema=False)
def work_authorize(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query("code"),
    scope: str = Query("user"),
    state: str | None = Query(None),
    code_challenge: str | None = Query(None),
    code_challenge_method: str | None = Query("S256"),
) -> HTMLResponse:
    return _authorize(
        "iManage Work (search & documents)", request,
        client_id=client_id, redirect_uri=redirect_uri, scope=scope, state=state,
        code_challenge=code_challenge, code_challenge_method=code_challenge_method,
    )


@router.post("/auth/oauth2/authorize/decision", name="work_authorize_decision", include_in_schema=False)
def work_authorize_decision(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(""),
    state: str | None = Form(None),
    code_challenge: str | None = Form(None),
    code_challenge_method: str | None = Form("S256"),
    decision: str = Form("approve"),
) -> RedirectResponse:
    return _authorize_decision("work", redirect_uri, scope, state, client_id, code_challenge, code_challenge_method, decision)


@router.post("/auth/oauth2/token", include_in_schema=False)
def work_token(
    grant_type: str = Form(...),
    code: str | None = Form(None),
    code_verifier: str | None = Form(None),
    refresh_token: str | None = Form(None),
) -> JSONResponse:
    return _token(grant_type, code, code_verifier, refresh_token)


# --- OAuth discovery documents ----------------------------------------------------

def _public_base(request: Request) -> str:
    # Behind App Service, TLS is terminated at the edge and the container sees http; honor the
    # X-Forwarded-Proto header so discovery URLs advertise the real https origin.
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{proto}://{request.url.netloc}".rstrip("/")


def _as_metadata(request: Request, authorize: str, token: str, scopes: list[str]) -> dict:
    base = _public_base(request)
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}{authorize}",
        "token_endpoint": f"{base}{token}",
        "scopes_supported": scopes,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
    }


@router.get("/.well-known/oauth-authorization-server", include_in_schema=False)
@router.get("/.well-known/oauth-authorization-server/mcp", include_in_schema=False)
@router.get("/.well-known/openid-configuration", include_in_schema=False)
def as_metadata_mcp(request: Request) -> JSONResponse:
    return JSONResponse(_as_metadata(request, "/mcp/oauth2/authorize", "/mcp/oauth2/token", ["imanage_search_mcp_scopes"]))


@router.get("/.well-known/oauth-authorization-server/auth", include_in_schema=False)
def as_metadata_work(request: Request) -> JSONResponse:
    return JSONResponse(_as_metadata(request, "/auth/oauth2/authorize", "/auth/oauth2/token", ["user"]))


@router.get("/.well-known/oauth-protected-resource/mcp/search", include_in_schema=False)
@router.get("/.well-known/oauth-protected-resource", include_in_schema=False)
def protected_resource_metadata(request: Request) -> JSONResponse:
    base = _public_base(request)
    return JSONResponse({
        "resource": base,
        "authorization_servers": [base],
        "scopes_supported": ["imanage_search_mcp_scopes"],
        "bearer_methods_supported": ["header"],
    })


def token_is_valid(authorization: str | None) -> bool:
    """True when a well-formed, unexpired mock access token is presented."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return False
    token = authorization.split(" ", 1)[1].strip()
    record = _TOKENS.get(token)
    return bool(record) and not record.get("refresh") and record.get("expires_at", 0) > time.time()
