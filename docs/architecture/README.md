# Architecture — iManage AI Workspace (Open-Network, Per-Customer Stamp)

This folder holds the architecture artifacts for the open-network, per-customer deployment
described in [`../product-spec.md`](../product-spec.md).

- [`architecture.mmd`](architecture.mmd) — Mermaid source (renders on GitHub).
- [`architecture.drawio`](architecture.drawio) — editable draw.io diagram.
- This README — the narrative walkthrough of the diagram.

## Design principles

1. **Open networking, functionality-first.** The web app and APIM are publicly reachable over
   HTTPS. The web app gates access with **Entra ID sign-in (App Service Authentication /
   EasyAuth)**; there is no VNet, VPN, private endpoint, or NAT gateway in this stamp.
2. **Everything data-plane goes through APIM.** The App Service proxy and the Foundry hosted
   agent never call iManage or models directly — all calls traverse **fine-grained APIM routes**
   for per-operation telemetry, policy, and rate limiting.
3. **Agent is not in the web app.** The grounded chat agent is **authored with Microsoft Agent
   Framework** but **deployed as a Foundry hosted agent**, with bring-your-own
   Storage/Cosmos/AI Search. Its **model inference is governed by the Foundry AI Gateway** —
   enabling AI Gateway on the Foundry resource and adding the project auto-proxies the project's
   model requests (agent turns included) through our APIM, with per-project token
   limits/quota. See [Configure AI Gateway in your Foundry resources](https://learn.microsoft.com/en-us/azure/foundry/configuration/enable-ai-api-management-gateway-portal)
   and [`../apim/README.md`](../apim/README.md) §3.2.
4. **Per-customer stamp.** One reusable Bicep + azd stamp per customer's single tenant; all
   firm-specific values are parameters.

## Trust boundaries

| Boundary | What crosses it | Control |
|---|---|---|
| User device → App Service | SPA/API traffic over HTTPS | Entra ID sign-in (EasyAuth) |
| Browser → iManage **authorize** | interactive OAuth login (MFA) | Public iManage endpoint |
| Stamp → iManage SaaS | token exchange + Work API + MCP | APIM public outbound |
| Stamp → Azure PaaS | Foundry, models | Public endpoints + Entra ID auth (keys disabled) |

## Request flows

### A. Sign-in (hybrid OAuth)
1. The browser signs in to the **App Service** with Entra ID, then hits `work/auth/start` and
   `auth/imanage/start` (Work API + MCP PKCE flows).
2. App Service redirects the **browser** to the iManage **authorize** endpoint (public) — the
   user completes login/MFA directly with iManage.
3. iManage redirects back to the App Service callback; App Service performs the **token
   exchange via APIM** (`/imanage/oauth/token`), where APIM injects the client secret and logs
   issuance (no token material).
4. Tokens are stored **per browser session** (isolated per user), never shared.

### B. Search / browse (data path)
Browser → App Service proxy → **APIM** (`/imanage/work/*` or `/imanage/mcp/*`) → iManage SaaS.
App Service attaches the session's iManage bearer; APIM adds the subscription key, policies, and
per-operation telemetry. A single customer-level call — no client-side fan-out.

### C. Agent turn (per-user token forwarding)
1. Browser → App Service `agent/.../turns` with the message + selected document ids.
2. App Service (the **agent bridge**) calls the **Foundry hosted agent** via **APIM `/agents`**,
   forwarding the user's short-lived iManage **MCP token** as the `imanageToken` **structured
   input** (never logged).
3. The hosted agent binds that token into its **iManage MCP tool** `Authorization` header and
   calls **APIM `/imanage/mcp`** to fetch document text as the signed-in user, then the **model**
   (governed by the **Foundry AI Gateway** → our APIM) to produce a grounded answer with citations
   + tool-run trace.
4. The answer returns through APIM → App Service → browser.

## Component inventory

| Component | SKU / mode | Network posture |
|---|---|---|
| App Service | Premium v3 (P1v3), Linux Python | Public HTTPS; Entra ID sign-in (EasyAuth) |
| API Management | Standard v2 | Public gateway |
| Azure AI Foundry | account + project | Public endpoints; Entra ID auth; BYO Storage/Cosmos/Search + capability host; keys disabled |
| Foundry hosted agent | Microsoft Agent Framework + `gpt-5.6-sol` (new agents / Responses API) | Runs in Agent Service; MCP tool via APIM |
| Log Analytics + App Insights | — | APIM + Foundry diagnostics, per-operation metrics |

> A fully-private topology (VNet, private endpoints, VPN, NAT) is out of scope for this
> open-network stamp.
