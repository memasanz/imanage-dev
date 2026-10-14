"""Tests for the fake iManage OAuth provider used to demo OBO without a real tenant."""
import base64
import hashlib
import importlib
import re
import secrets

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _pkce_pair():
    verifier = secrets.token_urlsafe(40)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def _run_consent(verifier, challenge):
    params = {
        "client_id": "demo-mcp-client",
        "redirect_uri": "https://app.example/callback",
        "scope": "imanage_search_mcp_scopes",
        "state": "xyz",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    page = client.get("/mcp/oauth2/authorize", params=params)
    assert page.status_code == 200 and "Approve" in page.text
    redirect = client.post(
        "/mcp/oauth2/authorize/decision",
        data={**params, "decision": "approve"},
        follow_redirects=False,
    )
    assert redirect.status_code == 302
    location = redirect.headers["location"]
    assert "state=xyz" in location
    return re.search(r"code=([^&]+)", location).group(1)


def test_authorization_code_pkce_flow_issues_token():
    verifier, challenge = _pkce_pair()
    code = _run_consent(verifier, challenge)
    token = client.post(
        "/mcp/oauth2/token",
        data={"grant_type": "authorization_code", "code": code, "code_verifier": verifier},
    ).json()
    assert token["token_type"] == "Bearer"
    assert token["access_token"].startswith("mock-at-")
    assert token["scope"] == "imanage_search_mcp_scopes"


def test_token_rejects_bad_pkce_verifier():
    _, challenge = _pkce_pair()
    code = _run_consent("unused", challenge)
    resp = client.post(
        "/mcp/oauth2/token",
        data={"grant_type": "authorization_code", "code": code, "code_verifier": "wrong-verifier"},
    )
    assert resp.status_code == 400


def test_discovery_documents():
    resource = client.get("/.well-known/oauth-protected-resource/mcp/search").json()
    assert resource["scopes_supported"] == ["imanage_search_mcp_scopes"]
    server = client.get("/.well-known/oauth-authorization-server").json()
    assert server["authorization_endpoint"].endswith("/mcp/oauth2/authorize")
    assert server["token_endpoint"].endswith("/mcp/oauth2/token")


def test_mcp_enforcement_toggle(monkeypatch):
    # Rebuild the app with enforcement on.
    monkeypatch.setenv("MOCK_REQUIRE_MCP_AUTH", "true")
    import app.main as main_module

    reloaded = importlib.reload(main_module)
    enforced = TestClient(reloaded.app)

    unauth = enforced.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert unauth.status_code == 401
    assert "WWW-Authenticate" in unauth.headers

    verifier, challenge = _pkce_pair()
    page_params = {
        "client_id": "demo-mcp-client",
        "redirect_uri": "https://app.example/callback",
        "scope": "imanage_search_mcp_scopes",
        "state": "xyz",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    enforced.get("/mcp/oauth2/authorize", params=page_params)
    redirect = enforced.post(
        "/mcp/oauth2/authorize/decision",
        data={**page_params, "decision": "approve"},
        follow_redirects=False,
    )
    code = re.search(r"code=([^&]+)", redirect.headers["location"]).group(1)
    access = enforced.post(
        "/mcp/oauth2/token",
        data={"grant_type": "authorization_code", "code": code, "code_verifier": verifier},
    ).json()["access_token"]

    ok = enforced.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search", "arguments": {"query": "merger"}}},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert ok.status_code == 200 and "result" in ok.json()

    # Restore default (enforcement off) for other tests.
    monkeypatch.delenv("MOCK_REQUIRE_MCP_AUTH", raising=False)
    importlib.reload(main_module)
