# iManage AI Workspace

A reusable Azure sample that gives a law firm's users a fast, modern way to
**search their iManage Work content** and **ask an AI agent grounded, cited questions** about the
documents they select. It pairs a unified iManage search/browse experience with a **Foundry hosted
AI chat agent**, and ships as a per‑customer deployment stamp that any iManage customer can deploy
into their own single tenant.

The repo includes a **standalone mock iManage upstream**, so search, browse,
document detail, and a deterministic chat demo run **without Azure or a live iManage tenant**.
Actual AI-generated chat requires a configured Foundry hosted agent and model deployment. When
you are ready, configure live backend URLs and per-user OAuth to point the same routes and
policies at a real iManage tenant and the real **iManage Work MCP Server**.

> **Status: demo/reference implementation, not a production-ready legal workspace.**
> This sample uses **open networking**. The stamp registers Work + MCP routes on your existing
> APIM; identity, OAuth, hosted-agent configuration, and model gateway governance need separate
> setup and verification. Local mock mode has no Entra sign-in or real access controls. A
> fully private, VNet‑isolated posture (private endpoints, VPN, NAT egress, per‑user token
> forwarding over a private MCP path) is the documented Sprint 2 target. See [`docs/product-spec.md`](docs/product-spec.md).

---

## What it does

- **Unified search** across Documents, Emails, Folders, Clients, and Matters — each with
  Keyword / Title / Author‑Typist / Number modes plus an advanced filter builder.
- **Matter & folder browsing** — Recent Matters feed and drill‑down into matter folders/documents.
- **Document detail** — versions, metadata/properties, and extracted text (MCP primary, Work API
  `/text` fallback).
- **Grounded AI chat** — select one or more documents as context and ask questions; answers cite
  their source documents and include a tool‑run trace with a correlation id.
- **Mock mode** for demos and validation without a live iManage tenant.

The front end is a **React/Vite** SPA with a modern, task‑oriented UX (deliberately *not* an
iManage‑UI clone).

---

## Architecture

```
Browser (HTTPS; configure Entra ID sign-in for deployed use)
  → Web app / UI  (App Service: FastAPI proxy + React SPA)
      ├─ APIM /imanage/work|mcp → mock upstream or live iManage
      ├─ Foundry hosted agent  → model + APIM /imanage/mcp
      └─ OAuth authorize/token → iManage or mock OAuth host (direct)

Agent turn:
  Web app → hosted agent Responses endpoint (or configured APIM override)
          → MCP tool → APIM /imanage/mcp → mock or live iManage MCP Server
```

Principles:

1. **Govern iManage data calls through APIM.** In Azure the proxy uses the
   `/imanage/work` and `/imanage/mcp` routes; configure the hosted agent's MCP URL to use the
   same gateway. Local mock development bypasses APIM. Model/agent gateway governance is
   separate setup; the full route catalog in the design docs includes deferred work.
2. **The agent is not in the web app.** The grounded chat agent is **authored with the Microsoft
   Agent Framework** and **deployed as a Foundry hosted agent**. Configure the **Foundry AI Gateway** separately
   if model inference must be governed through APIM.
3. **Backend‑swappable (mock *and* live).** A single `IMANAGE_BACKEND_MODE` switch (`mock` |
   `live`) selects the `/imanage/*` upstream, with identical routes, policies, and telemetry.
4. **Per‑customer stamp.** One reusable Bicep + azd stamp per customer's single tenant; all
   firm‑specific values are parameters.

Full narrative, trust boundaries, and request flows: [`docs/architecture/README.md`](docs/architecture/README.md)
(diagram sources: [`architecture.mmd`](docs/architecture/architecture.mmd),
[`architecture.drawio`](docs/architecture/architecture.drawio)).
APIM route/policy design: [`docs/apim/README.md`](docs/apim/README.md).

---

## Using the real iManage MCP Server

The grounded‑chat agent reads document text through the **iManage Work MCP Server** — iManage's
official Model Context Protocol endpoint for AI tools. In this solution the Foundry hosted agent's
MCP tool points at the **APIM `/imanage/mcp` route**, which proxies to the real iManage MCP Server
(`live` mode) or to the bundled emulator (`mock` mode).

### What iManage requires

Per [iManage's MCP Server documentation](https://docs.imanage.com/ai/mcpserver-admin-help/en-US/iManage_MCP_Server_Administration_Help.html):

- **OAuth 2.0 is mandatory.** Every search/fetch call must carry a valid iManage OAuth bearer
  token; there is no anonymous access. The server supports **OAuth 2.0 Dynamic Client
  Registration (DCR, RFC 7591)** so MCP clients can register and obtain credentials.
- **Permissions and ethical walls are enforced.** The MCP Server honors the signed‑in user's
  existing iManage permissions — if a user cannot see a document in iManage Work, they cannot
  reach it through MCP. This is why the agent runs with the **signed‑in user's own iManage token
  (forwarded per request)** rather than a shared application identity.
- **Every call is audited.** Search and fetch actions are logged by iManage for compliance; when
  access is revoked, tokens are destroyed.
- **Administrator setup.** The MCP Server must be enabled for your tenant, and an OAuth client
  (client id/secret, redirect URI, scopes) registered — via iManage Control Center or DCR. Obtain
  the MCP endpoint and client credentials from your iManage administrator.

### Tools exposed by the iManage MCP Server

The MCP Server implements the standard JSON‑RPC handshake (`initialize` → `tools/list` →
`tools/call`) and exposes two tools:

| Tool | Purpose | Key arguments |
|---|---|---|
| **`search`** | Find documents the user can access, by natural‑language question / keyword, optionally scoped to a library. | `question` (or `query`), `library` |
| **`fetch`** | Return a document's extracted text (chunked) and optional metadata. | `library`, `documentNumber` (document id), `textChunkIndex`, `includeMetadata` |

The bundled mock upstream emulates this exact contract (`search` + `fetch` over JSON‑RPC with an
OAuth challenge), so you can develop and demo against it and switch to the live server by
configuration only. See [`docs/apim/README.md`](docs/apim/README.md) §2 for the per‑operation APIM
mapping and [`docs/prereqs/imanage-oauth.md`](docs/prereqs/imanage-oauth.md) for the OAuth flows.

### Wiring it to `live`

Set your azd environment (see [`.env.example`](.env.example)):

```bash
azd env set IMANAGE_BACKEND_MODE live
azd env set IMANAGE_MCP_URL_LIVE https://<tenant>.cloudimanage.com/mcp
azd env set IMANAGE_SUBSCRIPTION_KEY <imanage-upstream-subscription-key>
# Separately configure backend WORK_* and MCP_* OAuth settings and tenant metadata.
```

These settings alone do not complete a live deployment. Configure the Work REST upstream,
customer/library metadata, OAuth clients and redirects, and the hosted agent; verify access
controls before using real documents. Store secrets in protected Azure settings, never in source.
See [`docs/prereqs/imanage-oauth.md`](docs/prereqs/imanage-oauth.md) for OAuth setup and
[`docs/apim/README.md`](docs/apim/README.md) §4 for the target named-value catalog.

---

## Repository layout

| Path | What it is |
|---|---|
| `src/frontend/` | React/Vite SPA (search, browse, document detail, Ask AI chat). |
| `src/backend/` | FastAPI proxy + static SPA host. Translates UI intent to iManage Work/MCP calls through APIM; manages per‑session OAuth tokens; bridges agent turns. |
| `src/mock_upstream/` | Standalone mock iManage Work REST + MCP JSON‑RPC upstream with in‑memory fake data. |
| `src/agent/` | Responses API reference implementation and private-network probes (not the active integration). |
| `agent-host/imanage-grounded-chat/` | Foundry **hosted agent** project (azd + `azure.yaml`) used by the configured backend. |
| `infra/` | Bicep + azd deployment stamp. |
| `docs/` | Product spec, architecture, APIM design, OAuth prereqs, security/WAF, rollout. |
| `config/` | Per‑tenant field‑map / library configuration. |

---

## Quickstart (mock mode, local)

Prerequisites: Python 3.11+ and Node.js 22.12+ (the current Vite dependencies do not support
Node 18). The optional hosted-agent project requires Python 3.13+ and its own Azure setup.

Run each service in its own terminal, starting at the repository root. On Windows PowerShell:

```powershell
# 1. Mock iManage upstream
cd src\mock_upstream
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --port 8080

# 2. Backend proxy (new terminal)
cd src\backend
python -m venv .venv
Copy-Item .env.example .env  # first setup only; do not overwrite existing settings
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000

# 3. Frontend (new terminal)
cd src\frontend
npm ci
npm run dev
```

On macOS/Linux use `cd src/mock_upstream` or `cd src/backend`, `python3 -m venv .venv`,
and `.venv/bin/python` in place of `.\.venv\Scripts\python`; copy backend settings with
`cp .env.example .env`. Frontend commands are unchanged.

Open http://localhost:5173, connect the mock Work + MCP connections, and search/browse the
synthetic dataset. Chat uses a deterministic stub until `FOUNDRY_PROJECT_ENDPOINT` and
`FOUNDRY_AGENT_NAME` are configured. No Azure credentials are needed for this local demo.

If your organization requires package mirrors, configure them locally; do not commit registry
credentials or organization-specific feed URLs.

Run the tests:

```powershell
# From the repository root; install the backend test runner once.
.\src\backend\.venv\Scripts\python -m pip install pytest==8.3.4
Push-Location src\backend
.\.venv\Scripts\python -m pytest -q
Pop-Location
Push-Location src\mock_upstream
.\.venv\Scripts\python -m pytest -q
Pop-Location
```

---

## Deploy to Azure (azd)

The stamp references a **bring‑your‑own Foundry project and APIM** and deploys the web + mock App
Services, registering the fine‑grained iManage routes onto your APIM.

Replace the placeholders in [`.env.example`](.env.example) with your own resource values
using `azd env set`; the example does not contain a working tenant or deployment credentials.

```bash
azd auth login
azd env new <environment-name>
# Set required values from .env.example with: azd env set <KEY> <value>
azd up
```

The Foundry **hosted agent** is provisioned and deployed separately from
`agent-host/imanage-grounded-chat/`; follow its [README](agent-host/imanage-grounded-chat/README.md).
That project's `azure.yaml` includes a specific model version and capacity; review availability,
quota, and cost before provisioning. Configure `FOUNDRY_AGENT_NAME` on the backend after deployment;
the root stamp does not set it. The deployment workflow is **manual-only** (`workflow_dispatch`);
configure your own repository variables and Azure federated identity before running it.
See [`docs/rollout.md`](docs/rollout.md) for the phased rollout and gates, and
[`infra/README.md`](infra/README.md) for infrastructure details.

---

## Documentation

- [`docs/product-spec.md`](docs/product-spec.md) — full product spec (behavior, iManage grammar, phased scope).
- [`docs/architecture/README.md`](docs/architecture/README.md) — architecture narrative + diagrams.
- [`docs/apim/README.md`](docs/apim/README.md) — APIM fine‑grained routes, policies, named values.
- [`docs/prereqs/imanage-oauth.md`](docs/prereqs/imanage-oauth.md) — iManage OAuth (Work + MCP) setup.
- [`docs/security/waf-checklist.md`](docs/security/waf-checklist.md) — Well‑Architected alignment.
- [`docs/rollout.md`](docs/rollout.md) — phased rollout / epics.

---

## Security notes

- Keep secrets out of source. Supply credentials through local ignored `.env` files or protected
  Azure settings. Key Vault-backed named values are part of the documented target design, not
  a guarantee that the active stamp has configured them.
- Configure and verify **Entra ID sign-in** (App Service Authentication / EasyAuth), session
  settings, and per-user OAuth before using real data. The mock accepts demo tokens and is
  not an authorization test.
- The agent accesses iManage **as the signed‑in user** — the web app forwards that user's iManage
  token to the hosted agent per request — so iManage permissions and ethical walls are always
  enforced.
- Verify deployed diagnostic policies do not record `Authorization`, `X-Auth-Token`, OAuth
  credentials, or forwarded MCP tokens. The policies and WAF checklist are design guidance,
  not a completed production security assessment.

## Sharing and licensing

Licensed under [MIT](LICENSE). Preserve existing third-party copyright notices; third-party
dependencies and assets remain subject to their own licenses. This sample is not an official
iManage product.

Publish source through Git, **not a ZIP of this working folder**. `.gitignore` excludes local
Azure state, `.env` variants, virtual environments, dependencies, generated frontend bundles,
browser captures, and diagnostic logs. The local presentation and root demo screenshot are also
excluded pending content/rights review; they have not been deleted.

Before the first public push, inspect `git status --short` and `git diff --cached`, run secret
scanning on the staged files, and review the remaining docs/assets for confidential content and
redistribution rights. If publishing an existing Git history from elsewhere, scan that history
too: ignore rules do not remove already-tracked files or historical secrets. Never publish real
client documents, tenant credentials, or deployment logs.
