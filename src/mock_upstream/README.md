# Mock iManage Upstream

Standalone FastAPI service that emulates enough of the classic iManage Work REST API and iManage MCP JSON-RPC surface for local and private full-stack validation without a live iManage tenant or internet egress.

## Run locally

```powershell
cd src\mock_upstream
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --port 8080
```

Open:
- Health: http://127.0.0.1:8080/health
- Swagger UI: http://127.0.0.1:8080/docs
- OpenAPI: http://127.0.0.1:8080/openapi.json

## Emulated surfaces

### Classic iManage Work REST (`/work/api/v2/`)

The mock accepts any `X-Auth-Token` value and returns raw iManage-like shapes, including coded profile fields and display-description siblings:

- `custom1` / `custom1_description` = client code / client name
- `custom2` / `custom2_description` = matter code / matter name
- `custom3` / `custom3_description` = practice area code / practice area name
- `custom4` / `custom4_description` = jurisdiction code / jurisdiction name
- `author` / `author_description`
- `class` / `class_description`

Implemented operations:
- `GET /work/api/v2/customers/{cid}/libraries`
- `POST /work/api/v2/customers/{cid}/documents/search`
- `GET /work/api/v2/customers/{cid}/documents/{docId}`
- `GET /work/api/v2/customers/{cid}/documents/{docId}/versions`
- `GET /work/api/v2/customers/{cid}/documents/{docId}/text`
- `GET /work/api/v2/customers/{cid}/documents/{docId}/download`
- `GET /work/api/v2/customers/{cid}/workspaces`
- `GET /work/api/v2/customers/{cid}/workspaces/{id}/children`
- `GET /work/api/v2/customers/{cid}/folders/{id}/children`
- `GET /work/api/v2/customers/{cid}/clients/search`
- `GET /work/api/v2/customers/{cid}/users/search`
- `GET /work/api/v2/customers/{cid}/users/me`

### iManage MCP (`/mcp`)

JSON-RPC 2.0 over HTTP with:
- `initialize` (returns `Mcp-Session-Id` header)
- `tools/list`
- `tools/call` for `search` and `fetch`

### Fake iManage OAuth provider (for demoing per-user token forwarding without a real tenant)

The mock also stands in as the iManage identity provider so the **whole per-user token-forwarding
flow** can be demoed end to end — the user completes a real OAuth2 Authorization Code + PKCE login
in the web app, the app exchanges the code for a token, and that token is forwarded to the hosted
agent and flows through APIM to the mock. Going to production is a pure config swap: point the
authorize/token URLs at `cloudimanage.com`.

Mirrors both real iManage OAuth surfaces (see `app/oauth.py`):

- **MCP client** (web-app Connect MCP; token forwarded to the agent): `GET /mcp/oauth2/authorize`, `POST /mcp/oauth2/token`
- **Work client** (web-app sign-in): `GET /auth/oauth2/authorize`, `POST /auth/oauth2/token`
- Discovery: `/.well-known/oauth-authorization-server[/mcp|/auth]`,
  `/.well-known/openid-configuration`, `/.well-known/oauth-protected-resource[/mcp/search]`

The `authorize` endpoints render a simple "Approve" login screen; the `token` endpoints verify
PKCE (S256) and issue opaque Bearer tokens. Every token resolves to a single demo user
(`Jordan Chen`). Tokens are in-memory and reset on restart.

Point the web app's `MCP_*` OAuth settings (and `WORK_*`) at these URLs for a demo:

| Web app setting | Demo value |
|---|---|
| `MCP_AUTH_URL` | `https://<mock-host>/mcp/oauth2/authorize` |
| `MCP_TOKEN_URL` | `https://<mock-host>/mcp/oauth2/token` |
| `MCP_SCOPE` | `imanage_search_mcp_scopes` |
| `MCP_CLIENT_ID` / `MCP_CLIENT_SECRET` | any non-empty value (the mock does not verify them) |

#### Prove the token actually flows

By default the MCP surface accepts any (or no) token, matching the simplest demo. Set
`MOCK_REQUIRE_MCP_AUTH=true` to make `/mcp` **reject** calls without a valid mock OAuth token
(401 + `WWW-Authenticate` challenge). Turn it on to visibly prove the forwarded user token is
reaching the mock through APIM; leave it off for a frictionless token-less demo.

## Dataset overview

The in-memory dataset includes 3 libraries (`ACTIVE_US`, `ARCHIVE_US`, `EU_WORK`), 25 documents across 5 clients and 8 matters, 5 email records, 6 users/authors, classes such as `DOC`, `EMAIL`, `PLEADING`, `CONTRACT`, and `MEMO`, plus workspace and folder hierarchies. IDs look like `ACTIVE_US!1001.1`; workspaces/folders use full library-qualified IDs like `ACTIVE_US!9001`.

## Docker

```powershell
docker build -t mock-imanage-upstream .
docker run --rm -p 8080:8080 mock-imanage-upstream
```
