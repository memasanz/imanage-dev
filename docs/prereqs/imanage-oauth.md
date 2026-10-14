# iManage OAuth — Deployment Prerequisites

The stamp authenticates each user to iManage with **their own** OAuth identity (Work API +
MCP), then **forwards that user's iManage MCP token** to the Foundry hosted agent per request
(per-user token forwarding — "the way iManage works"). The customer must register two OAuth
clients in their iManage Control Center **before** provisioning.

> Nothing here is a product decision — these are customer-supplied values wired in as parameters
> and Key Vault secrets. No client secret is ever committed to the repo.

> **Demoing without a real iManage tenant?** Skip §1–§3 and jump to §6 — the bundled mock
> upstream includes a fake iManage OAuth provider that exercises the identical Connect flow, so
> you point the web app at the mock and swap to `cloudimanage.com` later with no code change.

## 1. Clients to register

**Two separate iManage OAuth clients are required** — each with its own client id, client
secret, authorize/token endpoints, and consent. They are registered in iManage Control Center
(iManage is the IdP — **not** Entra).

| Client | Grant | Used by | Authorize / token base | Scope |
|---|---|---|---|---|
| **Work API client** | Authorization Code + PKCE | Browser sign-in → App Service (search, documents, matters, folders, users, libraries) | `https://cloudimanage.com/auth/oauth2/authorize` · `/token` | `user` |
| **MCP client** | Authorization Code + PKCE | **Web app sign-in → App Service** — token is then forwarded to the Foundry hosted agent for `search` / `fetch` grounding via iManage MCP | `https://cloudimanage.com/mcp/oauth2/authorize` · `/token` | `imanage_search_mcp_scopes` |

Both are confidential clients. The **authorize** step runs in a browser (interactive login +
MFA, direct to iManage), but the **token exchange + refresh** is server-to-server:

- **Work client** — exchanged by the App Service proxy through APIM `/imanage/oauth/token`
  (APIM injects the client secret from Key Vault; the browser never sees it).
- **MCP client** — exchanged the **same way by the App Service proxy** through APIM
  `/imanage/oauth/token`. The resulting per-user iManage MCP token is stored in the user's session
  and **forwarded to the hosted agent per request** (as the `imanageToken` structured input); the
  agent binds it into the MCP `Authorization` header. There is **no Foundry consent broker** — the
  web app owns both OAuth flows.

> The **authorize/token hosts live at `cloudimanage.com`** (not tenant-specific), while the
> **data hosts are tenant-specific** (`<tenant>.cloudimanage.com` for Work REST and
> `<tenant>.cloudimanage.com/mcp`). Only the data hosts flip behind APIM; auth is unchanged.

## 2. Redirect URIs

Each client whitelists a **different** redirect URI, but **both flows are completed by the App
Service** (one callback per surface).

**Work API client** → App Service callback:

```
https://<web-app-name>.azurewebsites.net/api/auth/work/callback
```

`<web-app-name>` is emitted as the `webAppName` deployment output. (For local development, also
allow `http://localhost:8000/api/auth/work/callback`.)

**MCP client** → App Service callback:

```
https://<web-app-name>.azurewebsites.net/api/auth/mcp/callback
```

(For local development, also allow `http://localhost:8000/api/auth/mcp/callback`.) After the user
completes this Connect flow, the per-user MCP token is forwarded to the agent on each turn — there
is no separate agent consent and no `-32006 / CONSENT_REQUIRED` gate.

## 3. Values the customer provides

Supplied as azd environment variables / App Service settings (non-secret) and Key Vault secrets:

| Setting | Type | Example |
|---|---|---|
| `WORK_AUTH_URL` | plain | `https://cloudimanage.com/auth/oauth2/authorize` |
| `WORK_TOKEN_URL` | plain | `https://cloudimanage.com/auth/oauth2/token` |
| `WORK_SCOPE` | plain | `user` |
| `WORK_CLIENT_ID` | plain | `a1b2c3...` |
| `WORK_CLIENT_SECRET` | **secret** → Key Vault `work-client-secret` | — |
| `MCP_AUTH_URL` | plain | `https://cloudimanage.com/mcp/oauth2/authorize` |
| `MCP_TOKEN_URL` | plain | `https://cloudimanage.com/mcp/oauth2/token` |
| `MCP_SCOPE` | plain | `imanage_search_mcp_scopes` |
| `MCP_CLIENT_ID` | plain | `d4e5f6...` |
| `MCP_CLIENT_SECRET` | **secret** → Key Vault `mcp-client-secret` | — |
| `IMANAGE_TENANT_HOST` | plain | `contoso.cloudimanage.com` |
| `IMANAGE_CUSTOMER_ID` | plain | `1` |
| `IMANAGE_LIBRARIES` | plain (comma list) | `ACTIVE_US,EU_WORK` |
| `IMANAGE_FIELD_MAP` | plain (JSON) | see product-spec §7.1 |

Because OAuth is direct (§4.1), the OAuth **client secrets do not go into APIM**:

- `WORK_CLIENT_SECRET` → App Service (via Key Vault reference `work-client-secret`); used by the
  backend's direct token exchange.
- `MCP_CLIENT_SECRET` → App Service (via Key Vault reference `mcp-client-secret`); used by the
  backend's direct MCP token exchange, the same path as the Work client.

The only APIM-side secret is `imanage-subscription-key` (data-plane), created empty by the `apim`
module and populated from Key Vault after it exists.

## 4. Token flows (summary)

> **Design decision — OAuth is direct; only data goes through APIM.** The interactive
> **authorize** and the back-channel **token exchange** both talk **directly** to the iManage
> OAuth host (`cloudimanage.com`, or the mock in demos). Only
> the **data plane** (Work REST + MCP `search`/`fetch`) is routed through APIM for per-call
> visibility and the mock/live flip. See §4.1 for why.

**Work API (web-app data path):**
1. Browser → App Service `/api/auth/work/start` → **PKCE** redirect to
   `cloudimanage.com/auth/oauth2/authorize` (interactive login + MFA, browser-direct).
2. iManage → `/api/auth/work/callback` with a code.
3. App Service exchanges the code **server-to-server, directly** against
   `cloudimanage.com/auth/oauth2/token` (Basic auth with the Work client secret + PKCE verifier).
4. Tokens are stored **per browser session** (in-memory, TLS-only, excluded from all logs). The
   session token is attached to `/imanage/work` and `/imanage/mcp` **data** calls the web app
   makes **through APIM**.

**MCP (agent per-user token-forwarding path):**
1. In the web app, the user clicks **Connect MCP** → **PKCE** redirect to
   `cloudimanage.com/mcp/oauth2/authorize` (interactive login, browser-direct) → back to
   `/api/auth/mcp/callback`.
2. App Service exchanges the code **server-to-server** through APIM `/imanage/oauth/token`, stores
   the per-user iManage MCP token in the session, and on each agent turn **forwards it to the
   hosted agent** as the `imanageToken` structured input (never logged).
3. The agent binds the forwarded token into its MCP tool's `Authorization: Bearer {{imanageToken}}`
   header and calls **APIM `/imanage/mcp`**. APIM forwards the token unchanged to the selected
   backend (mock ignores it; live iManage validates it) and threads `Mcp-Session-Id`. The token is
   scrubbed from all APIM logs.

The agent only ever addresses the APIM route for **data** — it never runs the OAuth dance or holds
iManage host URLs or secrets; the web app owns OAuth and forwards the resulting token.

### 4.1 Why OAuth is direct (not proxied through APIM)

The web app performs OAuth directly against iManage, separately from the APIM data routes:

- Authorize — browser redirect to `https://cloudimanage.com/mcp/oauth2/authorize`.
- Token — server-to-server exchange at `https://cloudimanage.com/mcp/oauth2/token`, using the client credentials and PKCE verifier. The Work OAuth flow follows the same pattern.

Reasons to keep it direct:

- **Authorize is interactive and host-specific.** It returns an HTML login/consent page and a
  302 redirect bound to the identity provider's origin. Proxying it through APIM hits a
  reverse-proxy base-path problem (the consent page's form action and redirect would resolve to
  the backend origin, not the gateway), with no telemetry benefit.
- **Token is a standards OAuth back-channel**, already TLS + PKCE + client-secret protected.
  Routing it through APIM adds no security and risks mangling the form-encoded body/redirects.
- **Visibility belongs on the data plane.** The calls worth metering per-operation are the Work
  REST and MCP `search`/`fetch` requests — those go through APIM. OAuth issuance is low-volume
  and already auditable at the identity provider.
- **Clean prod swap.** Going live changes only the OAuth host (mock
  → `cloudimanage.com`) and real client id/secret; the agent, APIM routes, and web app are
  untouched.

> **OAuth is direct; APIM governs the data plane.**

## 5. Mock vs. live — one route, flipped in APIM

The agent's MCP target is always APIM `/imanage/mcp`. Which backend that route hits is an **APIM
configuration flip** via the `imanage-backend-mode` named value — no agent redeploy:

| `imanage-backend-mode` | APIM `/imanage/mcp` backend | Auth |
|---|---|---|
| `mock` | mock App Service (`/mcp`) | token ignored; no iManage registration needed |
| `live` | `https://<tenant>.cloudimanage.com/mcp` | forwarded user token **required** and validated |

Use `mock` for demos and the Gate G1 networking/agent validation before customer OAuth clients
exist. Switch to `live` once both iManage clients (§1) and their redirect URIs (§2) are
registered.

## 6. Demoing per-user token forwarding without a real iManage tenant

The bundled **mock upstream** (`src/mock_upstream`) is a full stand-in: besides the Work REST +
MCP data surfaces, it runs a **fake iManage OAuth provider** that mirrors iManage's exact
endpoints (`/mcp/oauth2/authorize` + `/token`, `/auth/oauth2/authorize` + `/token`, and the
`/.well-known/*` discovery docs). This lets you demo the complete Connect + grounded-chat flow — real login
screen, PKCE code exchange, Bearer token, token passthrough through APIM — with **no iManage
tenant and no internet egress**.

**Point the web app's OAuth settings at the mock** (same `WORK_*` / `MCP_*` env vars as §3, with
authorize/token URLs set to `https://<mock-host>/...`). The agent's MCP tool URL
(`IMANAGE_MCP_URL`) points at **APIM `/imanage/mcp`** (same as production), or directly at the
mock `/mcp` for a frictionless local demo. No Foundry connection is involved.

**Prove the token is really flowing:** set `MOCK_REQUIRE_MCP_AUTH=true` on the mock App Service.
The MCP surface then rejects any call lacking a valid mock token (401 + `WWW-Authenticate`
challenge), so you can show that the forwarded user token genuinely reaches the backend through
APIM. Leave it unset for a frictionless token-less demo.

**Going to production is a config swap, not a code change:** repoint the web app's
authorize/token URLs to `https://cloudimanage.com/...`, supply the real client ids/secrets,
register the two App Service callbacks (§2) on the real iManage clients, point `IMANAGE_MCP_URL`
at the APIM `/imanage/mcp` route, and flip `imanage-backend-mode` to `live`. The agent, APIM
routes, and web app code are untouched.

### 6.1 Verified — per-user token forwarding (end-to-end, against the mock)

Token forwarding has been proven end-to-end:

- **Agent tool:** a direct MCP tool (`client.get_mcp_tool(name="imanage", url=IMANAGE_MCP_URL,
  headers={"Authorization": "Bearer {{imanageToken}}"}, approval_mode="never_require")`) — no
  Foundry toolbox or OAuth passthrough connection.
- **Token binding confirmed:** a direct Responses call with
  `extra_body={"structured_inputs": {"imanageToken": "mock-mcp-token"}}` returned
  `mcp_call fetch completed` and a grounded answer for `ACTIVE_US!1003.2`, with **no**
  `oauth_consent_request` item — proving the forwarded token binds into the MCP `Authorization`
  header and flows the whole path (web app → APIM → mock).

### 6.2 Verified — Web-app surface (end-to-end, through Easy Auth)

Per-user grounded chat has also been proven from the **web app**, so the same experience
works for an interactively signed-in user (not just direct Foundry calls):

- **Front door — Easy Auth (Entra):** the App Service is fronted by App Service Authentication
  (authsettingsV2, single-tenant Entra app registration). Unauthenticated requests get a `302`
  to `login.microsoftonline.com`; `/api/health` is the only excluded path (readiness probe).
- **Token passing:** on each agent turn the backend forwards the signed-in user's session iManage
  MCP token to the hosted agent's Responses endpoint as the `imanageToken` **structured input**
  (never logged); the agent binds it into the MCP `Authorization` header. The backend authenticates
  to Foundry with its **own** user-assigned managed identity (workload token, scope
  `https://ai.azure.com/.default`). *(An optional delegation path can also send the user's object id
  as `x-ms-user-identity` — see §6.2.1 — but the primary forward-token path does not require it.)*
- **Verified flow:** signed in as a tenant user → Connect Work + MCP → searched `merger` →
  selected *Project Falcon Merger Agreement* → asked a grounded question → the hosted agent
  (forwarded token through APIM to the mock) returned a grounded answer citing `ACTIVE_US!1001.3`
  with a correlation id. No `403`.

#### 6.2.1 OPTIONAL — custom impersonation role for `x-ms-user-identity` delegation

The primary design forwards the user's iManage token as a structured input (§6.2) and does **not**
need the role below. It is required **only** if you additionally delegate the end-user identity via
the `x-ms-user-identity` header, which is **gated by a data-plane permission that no built-in role
grants**. A middle-tier caller (the web app's managed identity) must then hold:

```
Microsoft.CognitiveServices/accounts/AIServices/agents/endpoints/UserIdentityImpersonation/action
```

Without it, the Responses call fails with
`403 forbidden — "Caller is not authorized to delegate to another user via the x-ms-user-identity header"`.
It is **not** covered by Foundry User / Foundry Owner / Cognitive Services User / Foundry Agent
Consumer. Grant it with a custom role assigned at the Foundry **account** (or specific agent)
scope:

```jsonc
// custom-impersonation-role.json
{
  "Name": "Foundry Agent User Identity Impersonation",
  "IsCustom": true,
  "Description": "Lets a trusted middle-tier service delegate the end-user identity to a hosted agent via x-ms-user-identity.",
  "Actions": [], "NotActions": [],
  "DataActions": [
    "Microsoft.CognitiveServices/accounts/AIServices/agents/endpoints/UserIdentityImpersonation/action"
  ],
  "NotDataActions": [],
  "AssignableScopes": [
    "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>"
  ]
}
```

```bash
az role definition create --role-definition custom-impersonation-role.json
az role assignment create \
  --assignee-object-id <web-app-managed-identity-principal-id> \
  --assignee-principal-type ServicePrincipal \
  --role "Foundry Agent User Identity Impersonation" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>
```

The web app MI also needs **Foundry Agent Consumer** + **Cognitive Services User** on the same
account (to interact with the agent endpoint and inference). RBAC propagation takes ~2–3 min.

> Delegation note (Foundry): the platform enforces a hard boundary only between delegated and
> non-delegated callers — it does **not** fence one delegated end user from another within a
> shared session. Give each end user their own session id to keep their data private.

Ref: [Hosted agent permissions — Delegate the end-user identity](https://learn.microsoft.com/azure/foundry/agents/concepts/hosted-agent-permissions#delegate-the-end-user-identity)
and [Isolate hosted agent sessions per user](https://learn.microsoft.com/azure/foundry/agents/how-to/isolate-sessions-per-user#isolate-sessions-for-your-own-users).
