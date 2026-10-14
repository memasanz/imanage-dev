# Product Spec — iManage AI Workspace (Best‑Practices Azure Solution)

## 1. Problem & Goal

**iManage AI Workspace** is a best-practices Azure solution that gives a law firm's
users a fast, modern way to search their iManage Work content and ask an AI agent grounded,
cited questions about selected documents. It combines a unified iManage search experience with a
hosted AI chat agent, delivered as a reusable per-customer deployment stamp. Sprint 1 ships with
**open networking** (public web app gated by Entra ID sign-in + public APIM gateway); a private,
VNet-isolated posture is the deferred Sprint 2 target.

**Goal:** Deliver a **reusable, best-practices deployment stamp** that any iManage customer can
deploy into **their own single tenant**, built in **two phases**:

- **Sprint 1 — Functionality first (open network).** Stand up the **four core components** —
  **Foundry** (hosted agent + model), **APIM** (fine-grained routes), the **UI / web app**, and
  the **mock iManage API** — with **public networking** (no VNet, VPN, or private endpoints). All
  backend traffic still flows through **APIM** with **fine-grained routes** (models, iManage Work
  API, iManage MCP) for per-call visibility. The goal is to prove the **full end-to-end
  functionality** — search, browse, document detail, and the grounded hosted-agent chat — quickly.
- **Sprint 2+ — Network isolation (deferred).** Layer in the private, VNet-isolated posture:
  APIM public access disabled behind a private endpoint, Foundry VNet injection with BYO
  resources, BYO-VNet, per-user OAuth on-behalf-of, NAT egress, and the private-MCP
  path. The full target design is retained below and in `docs/architecture/` as the Sprint 2
  blueprint; **`(Sprint 2 — deferred)` markers call out what is not built yet.**

Constant across both phases:
- The **AI agent runs as a Foundry hosted agent** (not in the web app).
- All backend data flows **through APIM** with **fine-grained routes** for visibility.
- A **React/Vite** front end with a **modern, task-oriented UX** (not an iManage-UI clone).
- The **mock iManage API** is a first-class, swappable APIM backend so the whole stack is
  demoable before wiring real iManage.

> This spec is self-contained: it defines the product's behavior, iManage API grammar, and Azure
> architecture directly. No external codebase is required to build it.

## 2. Confirmed Decisions

| Decision | Choice |
|---|---|
| IaC | **Bicep + azd** |
| Tenancy | **Per-customer deployment** — one reusable stamp per customer's single tenant |
| Edge access | **Sprint 1: open / public** (direct HTTPS to the web app + APIM public gateway). **Sprint 2 (deferred): fully private** — app + APIM private, reached only via private endpoint |
| Agent → iManage auth | **Per-user token forwarding ("the way iManage works")** — the web app authorizes the user to iManage in its own Connect flow, then forwards that user's iManage bearer to the hosted agent per request as the `imanageToken` structured input. The agent binds it into the iManage MCP `Authorization: Bearer {{imanageToken}}` header, so every call runs as the signed-in user. APIM forwards the bearer unchanged. **No interactive Foundry OBO consent gate** |
| Frontend | **React/Vite**, **modern, task-oriented UX** (not an iManage-UI clone) |
| Networking | **Sprint 1: open network — no VNet.** **Sprint 2 (deferred): managed VNet (stamp-created) for dev/demo; bring-your-own-VNet for enterprise** — see §13 for the decision guide |
| Deliverables | Architecture diagram, APIM route/policy design, Security & WAF alignment, phased rollout/epics |
| iManage login routing | **Direct OAuth** — both interactive **authorize** and back-channel **token exchange/refresh** talk directly to the iManage OAuth host (`cloudimanage.com`, or the mock in demos). Only the **data plane** (Work REST + MCP) is routed through APIM. See `docs/prereqs/imanage-oauth.md` §4.1 for rationale |
| Egress to iManage | **APIM owns the NAT Gateway path** for the **data plane** (`cloudimanage.com` Work API + MCP). OAuth authorize/token is direct (low-volume, PKCE + client-secret protected) |

## 2.1 Sprint 1 — current build scope (open network)

**In scope now (functionality-first, public networking):**

- **Four components only:** **Foundry** (hosted agent authored with **Microsoft Agent Framework**
  + a `gpt-5.6-sol` model deployment), **APIM** (fine-grained routes + policies + telemetry), the
  **UI / web app** (App Service: FastAPI proxy + React SPA), and the **mock iManage API**
  (emulates the Work REST + MCP surface).
- **Open network:** every component has **public network access**; no VNet, subnets, private
  endpoints, private DNS, VPN Gateway, or NAT Gateway.
- **All backend calls through APIM** on its **public** gateway, keeping the full fine-grained
  route / policy / telemetry design (`/models`, `/agents`, `/imanage/work`, `/imanage/mcp`).
- **Hosted agent via public MCP:** the Foundry hosted agent reaches the iManage MCP tool at
  **APIM's public `/imanage/mcp` route** — a **public MCP endpoint**, which is the first-class,
  supported Foundry path (no ACA shim, no dedicated MCP subnet). APIM proxies to the selected
  backend.
- **Backend-swappable, mock *and* live:** a single APIM backend setting selects the `/imanage/*`
  upstream — **`mock`** (the bundled emulator) or **`live`** (a real iManage tenant) — with
  **identical routes, policies, and telemetry**. Sprint 1 ships with `mock` as the default and
  the `live` wiring in place so a tenant can be swapped in by configuration, not redesign.
- **Full feature parity of the UI + agent chat** validated against the mock dataset.

**Explicitly deferred to Sprint 2+ (network isolation):**

- VNet + subnets, private endpoints, private DNS, APIM public-access-disabled, Foundry VNet
  injection + BYO Storage/Cosmos/Search, BYO-VNet, NAT egress + egress firewall.
- Per-user iManage **OAuth on-behalf-of** and the **private-MCP** path (internal Container Apps
  on a dedicated MCP subnet, DataProxy native routing).

> Sections **4, 6, 7, and 13** below describe the **Sprint 2 target** (private) design. Where a
> requirement is Sprint-2-only it is marked **(Sprint 2 — deferred)**. Sprint 1 implements the
> **same APIM routes and app/agent behavior**, just over **public** networking.

## 3. Functional Requirements

The solution must deliver the following capabilities:

- **Unified search** across Documents, Emails, Folders, Clients, Matters, each with
  Keyword / Title / Author‑Typist / Number modes + an Advanced filter builder.
- **iManage grammar rules** (the proxy must honor these when translating UI intent to Work API calls):
  - Author/Typist → `owner` (not `author`); resolve names/emails → user ids.
  - Documents Title → `*term*`; Matters Title → bare `name`; Matters Keyword → `anywhere`.
  - Documents vs Emails server-side (`exclude_emails` vs `email_only` + `group_by_conversation=false`).
  - Library scoping = single comma `libraries` param on one customer-level call.
  - Number search → `document_number`; keyword negation → `NOT term`.
  - Folder `type=regular,search` only for all-libraries; folder "open" needs full id (`LIB!num`).
  - Uses the **classic** `/work/api/v2/` surface (X-Auth-Token), not the web/XSRF surface.
- **Matter & folder browsing** — Recent Matters feed, drill into matter folders/documents.
- **Multi-library** scoping; **user/library/profile-field** lookups (configurable `customN` → semantic label mapping).
- **Document detail** — versions, extracted text (MCP primary, Work API `/text` fallback, chunked fetch).
- **AI agent chat** — select 1+ documents as context, ask grounded questions, answers cite source
  docs with tool-run trace + correlation id.
- **Mock mode** for demos and validation, at **two levels**: (a) in-process `MOCK_MODE` (backend
  serves fake data directly, no APIM), and (b) a **standalone mock iManage upstream** behind APIM
  for full-stack validation without a live tenant (see §4.1).
- **Health/diagnostics** endpoints and per-route telemetry.

## 4. Target Architecture

> **Sprint 1 (current) uses the simplified open-network topology in §4.0.** The detailed design
> in §4.1–§4.4 is the **Sprint 2 target** (private, VNet-isolated) — retained as the blueprint
> we grow into. Sprint 1 keeps the same APIM routes, agent, and app behavior over public
> networking.

### 4.0 Sprint 1 architecture (open network — current build)

Four public components; all backend data still flows through APIM for fine-grained visibility:

```
Browser (public HTTPS)
  → Web app / UI  (App Service: FastAPI proxy + React SPA)
      → APIM (public gateway, fine-grained routes + policies + telemetry)
          ├─ /models            → Foundry model (gpt-5.6-sol)
          ├─ /agents            → Foundry hosted agent (Agent Framework)
          └─ /imanage/work|mcp|oauth → backend switch → mock  (Sprint 1 default)
                                                       \→ live iManage (swap by config)

Agent turn:
  Web app → Foundry hosted agent → MCP tool.server_url = APIM public /imanage/mcp
          → APIM → (mock | live iManage)
```

- **Foundry hosted agent (Agent Framework):** the grounded chat agent runs in Foundry Agent
  Service (new agents / Responses API), not in the web app. Its MCP tool points at **APIM's
  public `/imanage/mcp`** — a public MCP endpoint, the supported path — so every tool call is
  proxied and logged by APIM. Model inference is reached via APIM `/models`.
- **APIM (public):** public network access **enabled**; same five APIs and policies as the
  Sprint 2 design. It is the single choke point for visibility.
- **UI / web app (public):** App Service hosting the FastAPI proxy + React SPA. All its upstream
  calls go through the APIM base URL. Public access enabled; no VNet integration.
- **Mock iManage API (public):** standalone App Service emulating the Work REST + MCP surface,
  wired as the default APIM `/imanage/*` backend. The **`live`** backend (real iManage) is
  selectable by the same backend setting — identical routes/policies/telemetry.
- **Deferred (Sprint 2):** VNet, private endpoints, NAT, Foundry injection, private MCP path — see §4.1+.

### 4.1 Logical components

- **Private DNS zones** linked to the VNet for every private-endpoint service.
- **App Service (Linux, Python)** — FastAPI **proxy + SPA host**; **no agent logic**.
  VNet-integrated (outbound) + **private endpoint** (inbound); public access disabled.
- **APIM Standard v2** — **public network access disabled**, **inbound private endpoint**,
  **outbound VNet integration**. Hosts all fine-grained APIs and policies.
- **Azure AI Foundry** (account + project) — **network-injected into the VNet** with
  **bring-your-own resources** (BYO Storage, Cosmos DB, AI Search) for Agent Service threads;
  **private endpoints** for the account; public access disabled. Follows the Microsoft Foundry
  **"standard agent with tools behind VNet"** reference pattern — specifically
  [`19-private-network-agent-tools`](https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/19-private-network-agent-tools)
  (BYO-VNet + subnet delegation + private endpoints + Capability Host). **This tools-behind-VNet
  pattern is required** because the hosted agent calls a **private MCP tool** (iManage) — the
  simpler "standard agent" pattern that does **not** support tools behind a VNet is insufficient
  here.
  - **Network injection is set at account creation and CANNOT be added later.** The enabler is a
    property on the `Microsoft.CognitiveServices/accounts` resource:
    `networkInjections: [{ scenario: 'agent', subnetArmId: <snet-agents>, useMicrosoftManagedNetwork: false }]`.
    Because it is immutable post-create, a Foundry account provisioned without it (e.g. a bare
    private account) **must be deleted and recreated** to gain agent VNet injection — along with
    its project, model deployment, capability host, and private endpoints. **Design the stamp so
    the Foundry account is created with injection from the start.**
  - **Capability Host + RBAC ordering (from template 19):** the capability host binds the BYO
    Cosmos/Storage/Search connections to the project. The **Cosmos DB Operator** role must be
    assigned to the project identity **before** the capability host is created; **Storage Blob
    Data Owner** and the **Cosmos Built-In Data Contributor** (scoped to the project workspace
    containers) must be assigned **after**. Getting this order wrong fails capability-host
    creation.
- **Foundry Hosted Agent** — the grounded chat agent, running in Foundry Agent Service, using
  the **iManage MCP tool** + a **model deployment**. The agent runs here, not in the web app.
  **Agent model:** use the **new agents** surface (Responses API + versioned persistent agents,
  `azure-ai-projects>=2.0.0`), **not** the classic Assistants API (`asst_` ids, threads/runs).
  Private MCP tool support applies to the **new** agents only; a classic agent cannot use a
  tool behind the VNet.
  **Critical networking fact:** for a **private MCP tool**, Foundry's **DataProxy** (Tool Server
  connector) resolves DNS at the **Foundry infrastructure level, not through the VNet's private
  DNS zones**. The tool must therefore be reachable by **native VNet routing** — the validated
  pattern is an **internal Container Apps environment** (no public endpoint; private FQDN resolves
  only in-VNet; DataProxy routes to it natively). A locked-down **private-endpoint-only** service
  is rejected by the DataProxy (observed as `424 Failed Dependency` —
  *"Error retrieving tool list from MCP server"* — when pointed straight at private APIM, or
  `403 Ip Forbidden` for a private-endpoint-only Function App). The MCP tool must also implement
  **Streamable HTTP transport** (JSON-RPC over HTTP with `Mcp-Session-Id` session management).
- **Key Vault** (private endpoint) — iManage client secrets, APIM subscription keys, config.
- **NAT Gateway** — the stamp's **standard, always-deployed** outbound egress for the VNet
  subnets that need internet access. It provides a **stable, dedicated public source IP** (ideal
  for iManage-side IP allow-listing) and a large SNAT pool; it is an egress **enabler, not a
  filter** — it does **not** restrict destinations. Associated with the **APIM outbound** path for
  the iManage **data plane** (`cloudimanage.com`: Work API + MCP), and with
  other subnets (e.g. App Service / agents) that require outbound. OAuth token exchange is
  server-side but **direct** (App Service / Foundry → iManage), so it also rides NAT where
  applicable; the interactive authorize redirect rides the user's own browser/internet, not the
  VNet. **Destination filtering is a
  separate, opt-in control (`deployEgressFirewall`, default off)** via Azure Firewall FQDN rules;
  when the firewall is enabled it sits in front of the NAT egress path. NAT (stable source IP) and
  Firewall (destination allow-list) are complementary.

> **Why egress is needed at all:** iManage Cloud is public SaaS (no Private Link), so reaching it
> requires outbound internet from the VNet. Azure retired free default outbound access (Sep 2025),
> so an **explicit** egress method is required — NAT Gateway is deployed as the standard default so
> the stamp works out of the box and presents a stable egress IP for iManage allow-listing.
- **Observability** — Log Analytics workspace + Application Insights; APIM & Foundry diagnostics;
  per-route/per-operation logging for fine-grained visibility.
- **Managed identities** (user-assigned) for App Service, APIM, and Foundry → model/ACR/Key Vault RBAC.
- **Mock iManage Upstream** *(first-class, independently-deployable service; `imanageBackendMode`
  param)* — its **own** App Service/container (separate azd service, own Bicep module, own private
  endpoint) that **emulates the iManage Work REST API + MCP JSON-RPC surface** with a built-in
  fake dataset. It is a **swappable APIM backend**: the Work and
  MCP APIs resolve their backend to either this mock (`mock`) or real iManage (`live`) via a
  single parameter — **same routes, same policies, same telemetry**, so you can validate the full
  stack end-to-end, watch the traffic through APIM, then **swap in real iManage with no route or
  policy change**. Runs inside the VNet with **no internet egress** in `mock` mode. Distinct from
  the backend's in-process `MOCK_MODE` (which short-circuits before APIM).

### 4.2 Network topology (subnets)

| Subnet | Purpose | Notes |
|---|---|---|
| `snet-apim` | APIM Standard v2 outbound VNet integration | delegated to APIM |
| `snet-privateendpoints` | PEs for APIM inbound, App Service, Foundry, Key Vault, Storage, Search | |
| `snet-appservice` | App Service regional VNet integration (outbound) | delegated `Microsoft.Web/serverFarms` |
| `snet-agents` | Foundry Agent Service network injection | delegated per Foundry BYO-network |
| `snet-nat` / NAT Gateway assoc. | egress to iManage SaaS | stable outbound IP(s) |

BYO-VNet option: all subnet names/prefixes are parameters; stamp consumes an existing VNet +
pre-created delegated subnets instead of creating them.

### 4.3 Request & auth flows

**A. User sign-in (browser):**
1. Browser → App Service (private) `/.../work/auth/start` and `/.../auth/imanage/start`.
2. App Service issues **PKCE** OAuth redirects to iManage **authorize** endpoint
   (`cloudimanage.com`) — browser completes login/MFA directly with iManage (public authorize).
3. iManage redirects back to App Service callback; **token exchange is server-to-server
   directly against iManage** (`cloudimanage.com/auth/oauth2/token`, Basic-auth client secret +
   PKCE). Not proxied through APIM (see §4.1 of the OAuth prereqs).
4. Tokens stored **per browser session** (isolated), never shared across users. Secrets
   (client secret) sourced from Key Vault.

**B. Search / browse (data path):**
Browser → App Service proxy → **APIM fine-grained route** → iManage Work API / MCP.
App Service attaches the session's iManage token; APIM adds subscription key + policies +
per-operation telemetry. Single customer-level call (no client fan-out).

**C. Agent turn (per-user token forwarding):**
1. Browser → App Service `/agent/.../turns` with message + selected document ids.
2. App Service calls the **Foundry hosted agent** via **APIM `/agents` route**, passing the
   message + document context (ids/metadata) **and the signed-in user's iManage bearer as the
   `imanageToken` structured input** (never logged).
3. The agent's iManage MCP tool is a **direct MCP tool** pointed at **APIM `/imanage/mcp`** with a
   templated `Authorization: Bearer {{imanageToken}}` header. Foundry substitutes the per-request
   `imanageToken` into that header, so every MCP call carries the **signed-in user's own iManage
   token** — the agent reads document text strictly as that user. There is **no interactive Foundry
   OBO consent gate**: the user authorizes iManage once in the web app's own Connect flow.
   The agent then calls its **model** to produce a grounded
   answer with citations + tool-run trace. Because the project is **added to the Foundry AI
   Gateway** (Manage → AI Gateway, bound to our private APIM), the agent's **model requests are
   automatically proxied through APIM** at the project level, so token-limit/quota/metric policies
   are **enforced** on agent turns — not just observed.
4. Answer returns through APIM → App Service → browser.

> **How agent token governance works (Foundry AI Gateway):** enabling **AI Gateway** on the
> Foundry *resource* and adding the *project* routes **all** of that project's requests —
> including the hosted agent's model inference — through the associated APIM instance
> automatically, with **per-project** TPM + token quota. This is the first-class Foundry feature
> (*Manage → AI Gateway*), distinct from APIM-side "Import Azure AI Foundry." Use **"Use existing
> APIM"** = our private **Standard v2** instance (APIM must be privately reachable when Foundry
> public access is disabled). Governing the **MCP tool** through the gateway is a **preview** path;
> our `/imanage/mcp` APIM route gives per-call tool visibility regardless.

### 4.3.1 iManage MCP dynamic discovery

The MCP integration is **discovery-driven**, not statically pinned. Three layers:

1. **OAuth protected-resource metadata (RFC 9728).** Before the MCP authorize redirect, the
   backend calls `GET /.well-known/oauth-protected-resource/mcp/search` (APIM op
   `mcp-resource-metadata`) to learn the `resource` identifier and `scopes_supported`
   dynamically. Static `MCP_RESOURCE`/`MCP_SCOPE` are **fallbacks** only if discovery fails.
2. **Session/endpoint discovery.** The JSON-RPC `initialize` call may return a `3xx` redirect to
   a per-session endpoint; the backend follows the `location` and captures the **`Mcp-Session-Id`**
   header, reusing both on all subsequent calls. **APIM must preserve `Mcp-Session-Id` and allow
   the redirect** (see `docs/apim`).
3. **Tool discovery.** `tools/list` is called before `tools/call` so the available tools
   (`search`, `fetch`, …) are enumerated at runtime rather than hardcoded.

Implication for the hosted agent: its MCP tool uses the same discovery sequence under the user's
forwarded iManage token, so no MCP endpoint, scope, or tool list is baked into the stamp — only
the MCP server host is configured.

### 4.4 Architecture diagram

A draw.io + mermaid diagram will be produced in `docs/architecture/` showing: browser →
(public) App Service → (public) APIM → fine-grained routes to Foundry (models + agents) and out
to iManage Work API / MCP / OAuth, with Log Analytics. (Mermaid draft included in the spec
appendix during Epic 1.)

## 5. APIM Design — Fine-Grained Routes & Policies

### 5.1 APIs (each as a distinct APIM API, operations named for telemetry)

| APIM API | Path prefix | Backend | Operations (fine-grained) |
|---|---|---|---|
| **Models** | `/models` | Foundry (private) | `chat-completions` (used today); `responses`, `embeddings` (optional/forward-looking) — serves **both** the hosted agent's model turns and any app-initiated model calls |
| **Agents** | `/agents` | Foundry Agent Service | `create-thread`, `run-turn`, `get-run`, `list-messages` |
| **iManage Work** | `/imanage/work` | `*.cloudimanage.com/work/api/v2` (NAT egress) | `documents-list`, `documents-list-scoped`, `documents-recent`, `documents-checkedout`, `documents-favorites`, `document-get`, `document-versions`, `document-text`, `document-download`, `workspaces-search`, `workspaces-recent` (`/recent-workspaces`), `workspace-documents`, `workspace-children`, `folders-search`, `folder-children`, `clients-search` (`/customs/custom1/search`), `users-search` (`/libraries/{lib}/users`), `user-profile` (root `/api`), `libraries` — **19 ops, all GET** |
| **iManage MCP** | `/imanage/mcp` | `*.cloudimanage.com/mcp` (NAT egress) | `initialize`, `list-tools`, `search`, `fetch`, `call-tool` (single JSON-RPC endpoint; `Mcp-Session-Id` + 3xx redirect preserved) |
| **iManage OAuth** | _(not in APIM)_ | iManage auth host — **direct** | OAuth authorize + token exchange are **direct** to `cloudimanage.com`, not proxied. See `docs/prereqs/imanage-oauth.md` §4.1 |

Fine-grained operations give per-call metrics, logs, rate limits, and traceability. Production
document **search is `GET /documents`** with params (the `POST /documents/search` surface is
diagnostics-only and intentionally excluded). Full catalog + reconciliation: [`docs/apim`](apim/README.md).

**Swappable iManage backend.** The Work and MCP APIs resolve their backend through APIM
**backend entities** (`imanage-work-backend`, `imanage-mcp-backend`) selected by the
`imanageBackendMode` parameter:
- `mock` → the **Mock iManage Upstream** private endpoint (no egress).
- `live` → `{tenant}.cloudimanage.com` via NAT egress.

Routes, operations, and policies are **identical** in both modes, so the same telemetry proves
the stack before pointing at the real tenant. Switching is a one-parameter backend change — no
API or policy edits.

### 5.2 Policy design (per scope)

- **Global/all APIs:** `set-backend-service` to private backends; `cors` (same-origin only);
  `correlation-id` propagation; `rate-limit-by-key` / `quota-by-key` (per subscription); emit
  custom metrics (`api`, `operation`, `library`, `status`).
- **Models/Agents:** **baseline policies come from the Foundry ↔ APIM AI Gateway integration**
  (APIM *Import Azure AI Foundry*): managed-identity auth, `llm-token-limit` (token rate/quota),
  `llm-emit-token-metric` (token usage), backend-pool load-balancing + circuit breaker, optional
  content-safety. **Semantic caching is not used** for this solution. Our deltas: `correlation-id`
  propagation, custom metric dimensions, and the agent `run-turn` forwarded-token / no-log-body rule.
  - **Hosted-agent model calls are routed through `/models` too.** The Foundry project's model
    **connection targets the APIM `/models` endpoint** (not the raw in-account deployment), so the
    agent's inference transits APIM and the `llm-token-limit`/`llm-emit-token-metric` policies
    **enforce + measure** agent token usage. Linking APIM to Foundry alone does **not** achieve
    this — it only fronts callers that use the APIM URL; the connection is what puts the agent's
    model path through APIM.
  - **Keying for enforcement:** token limits/quota are applied `by-key` — use the **stamp
    subscription key** for per-deployment caps, or key on the **signed-in user identity** (JWT claim /
    forwarded header) for **per-user** caps. Document which key a customer wants at deploy time.
  - **Trade-off:** adds one in-VNet hop per turn; APIM must be reachable from the agents subnet
    (it is — APIM is private in-VNet). Validated at **Gate G1**.
- **iManage Work/MCP:** attach `Ocp-Apim-Subscription-Key`; forward caller's iManage bearer
  (`X-Auth-Token`/`Authorization`) unchanged; strip hop-by-hop headers; scrub tokens from logs;
  per-operation diagnostic logging (method, path, status, latency, library). **MCP:** preserve
  the `Mcp-Session-Id` header and allow the `initialize` 3xx redirect (session discovery).
- **OAuth token:** separate Work and MCP clients; inject the correct client secret from Key Vault
  (named value backed by KV); `mcp-resource-metadata` is an unauthenticated GET used for RFC 9728
  discovery; never return secrets to the client; log issuance events without token material.
- **Security:** `validate-jwt`/IP allow-list optional; `public network access = Disabled`;
  all backends reached via VNet/private endpoints.

## 6. Identity, Secrets & iManage OAuth

- **Managed identities (UAMI):** App Service → Key Vault (get), Foundry model (Cognitive
  Services OpenAI User), ACR (AcrPull for hosted agent image if applicable). APIM → Key Vault
  named values + Foundry. Foundry project SA identity → ACR/BYO storage/Cosmos/Search per
  hosted-agent requirements.
- **Key Vault (private endpoint):** `WORK_CLIENT_SECRET`, `HOSTED_MCP_CLIENT_SECRET`,
  `APIM_SUBSCRIPTION_KEY`; referenced via App Service Key Vault references + APIM named values.
- **iManage app registrations (customer-provided):** Work OAuth client (PKCE) + MCP OAuth
  client; redirect URIs point to the App Service host. Documented as a
  deployment prerequisite with exact redirect URI format.
- **Per-user token handling:** for the **web app's own** Work/MCP calls, the user's iManage token is
  per-request, in-memory, TLS-only, and excluded from all logs/telemetry. For the **agent**, the
  web app forwards that same user token as the `imanageToken` **structured input** on each turn;
  the agent binds it into the MCP `Authorization` header and APIM forwards it unchanged to iManage.
  The token is never logged by the web app, the agent, or the APIM policies on `/agents` and
  `/imanage/*`. (iManage bearers are short-lived; structured-input values must never be logged.)

## 7. Backend (App Service) — Proxy

- FastAPI service: OAuth start/callback/status/logout, per-session token store, Work API proxy
  endpoints (search/documents/workspaces/folders/clients/users/libraries), MCP search/fetch,
  context set/get/clear, and an **agent bridge** that forwards turns to the Foundry hosted agent
  via APIM.
- Serves the built SPA (`/ui/`) and `/health`; exposes `GET /config` (active neutral fields +
  display labels + per-field flags) so the SPA renders tenant fields dynamically (see §7.2).
- All upstream calls go through **APIM base URL**; no direct iManage/Foundry calls.
- Mock mode available (built-in fake iManage dataset + optional real model) for demos.
- Config via App Service settings + Key Vault references; BYO/firm-specific values
  (libraries, `customN` field map) externalized — nothing firm-specific baked in.

### 7.1 Tenant configuration (libraries & profile fields)

iManage **libraries (databases)** and **`customN` profile-field meanings** are firm-specific and
must never be baked into the repo. The solution treats them as runtime configuration (defaults
blank/neutral):

| Setting | Meaning | Default | Source |
|---|---|---|---|
| `IMANAGE_CUSTOMER_ID` | iManage customer/tenant id | none (required for `live`) | azd param / app setting |
| `IMANAGE_LIBRARIES` | libraries the stamp scopes across; defines the "all-libraries" set so the filter can be omitted | empty → all discovered | azd param / app setting |
| `IMANAGE_FIELD_MAP` | JSON array mapping each neutral field → its iManage `customN` source + label + flags (see schema below) | `[]` (nothing mapped) | azd param / app setting (or App Configuration) |

**How iManage returns profile-field values (API shape).** The Work API returns each profile
field as a **correlated pair** on every document/workspace record — a coded value plus a
human-readable sibling:

| Returned field | Example | Role |
|---|---|---|
| `customN` | `"custom1": "412117"` | the **coded id/value** — what you **filter & search** on |
| `customN_description` | `"custom1_description": "Acme Corp"` | the **display text** — what the user reads |

Standard fields follow the same convention (`author` + `author_description`, `class` +
`class_description`). On **search** you filter by the code (`{"filters": {"custom1": "412117"}}`
or `{"profile": {"custom1": …}}`); on **render** you show the `_description`. A single `customN`
code therefore resolves to **two** source fields, which the field map must capture.

**`IMANAGE_FIELD_MAP` schema** — one object per neutral field:

```json
[
  { "key": "client", "source": "custom1",
    "value_from": "custom1", "label_from": "custom1_description",
    "label": "Client", "searchable": true, "filterable": true, "show_in_detail": true },
  { "key": "matter_lead", "source": "custom5",
    "value_from": "custom5", "label_from": "custom5_description",
    "label": "Responsible Attorney", "searchable": false, "filterable": true, "show_in_detail": true }
]
```

- `value_from` defaults to `source`; `label_from` defaults to `"<source>_description"` — so a
  minimal entry can supply just `key` + `source` + `label`.

- **Libraries:** the SPA library picker is populated **live via `GET /libraries`**; the config
  list is only used to compute the "all-libraries" default scope (optional allowlist to constrain).
- **Profile fields:** which `customN` carries Client/Matter/etc. is firm-defined and not reliably
  discoverable, so it stays config defaulting to empty — a tenant supplies `IMANAGE_FIELD_MAP` in
  its private environment; the repo exposes nothing.
- **Mock upstream:** emits **neutral semantic keys** (client/matter/…) and a fixed library set, so
  it needs **no field map**; its Swagger documents the neutral shape. This is why mock mode
  works with zero firm config.

**Where the config physically lives (recommended):**
- **Non-secret config** (`IMANAGE_CUSTOMER_ID`, `IMANAGE_LIBRARIES`, `IMANAGE_FIELD_MAP`) is
  authored per-stamp in the customer's **azd environment** (`azd env set …` → `.azure/<env>/.env`),
  flowed through **`infra/main.parameters.json`** → Bicep → **App Service application settings**.
  Redeployable, diff-able, and nothing firm-specific in the repo (defaults blank).
- **Secrets** (`WORK_CLIENT_SECRET`, `HOSTED_MCP_CLIENT_SECRET`, `APIM_SUBSCRIPTION_KEY`) live in
  **Key Vault**; the matching App Service settings hold **`@Microsoft.KeyVault(...)` references**,
  never literals (§6).
- **Optional (fleets):** customers managing many stamps may centralize `IMANAGE_FIELD_MAP` (and
  other non-secret config) in **Azure App Configuration** (labelled per environment) instead of
  per-app settings — an opt-in upgrade, not the default.

### 7.2 Mapping custom fields to the frontend

The SPA must **never see raw `customN`** — it renders from neutral keys + metadata:

1. **Normalize in the backend.** Each proxy response resolves every mapped field's **code**
   (`value_from`) and **display text** (`label_from`) into a single neutral object, e.g.
   `custom1="412117"` + `custom1_description="Acme Corp"` → `{ "client": { "id": "412117", "text":
   "Acme Corp" } }`. Single translation point; the UI never learns which custom number was used,
   but the code is preserved so filtering still works.
2. **Expose a UI-config endpoint.** `GET /config` returns the **active** neutral fields, their
   **display labels**, and per-field flags (`searchable`/`filterable`/`show_in_detail`) — a
   first-class, cacheable contract for the SPA.
3. **Render dynamically.** Search columns, the advanced-filter builder options, and the
   document/matter detail panel are built from that field list — **unmapped fields never render**,
   newly mapped fields appear automatically. No hard-coded field list in the SPA. The UI shows
   `text`; when a filter fires it sends the neutral key and the backend translates back to the
   `customN` code for the iManage query.
4. **Labels are config too.** Each entry's `label` (e.g. `"Responsible Attorney"`) lets a firm
   relabel a neutral key without code; a blank label falls back to the neutral key.

> Example: a firm adds `{ "key": "matter_lead", "source": "custom5", "label": "Responsible
> Attorney", "filterable": true, "show_in_detail": true }` → a "Responsible Attorney" column +
> filter appear automatically, showing `custom5_description` and filtering on `custom5`; a firm
> leaving it out sees nothing. The mock upstream returns neutral keys directly, so the same SPA
> renders it unchanged.

## 8. Frontend — React/Vite (modern, task-oriented UX)

**Design stance:** deliver a **clean, modern, task-oriented experience** that is genuinely easy
to use — **not a clone of the cloudimanage.com UI**. Rather than iManage's dense, tab-heavy
desktop layout, the product leads with search and the AI agent and surfaces capabilities (search
grammar, browsing, document context, agent chat) through a streamlined interface.

**Experience principles:**
- **One search box, smart intent.** A single prominent search with lightweight scope chips
  (Documents / Emails / Matters / Folders / Clients) and an optional "Advanced" drawer. The
  underlying iManage grammar (owner vs author, title wildcarding, `anywhere`, number search,
  negation, library scoping) is honored by the proxy and surfaced through simple controls, not
  raw syntax.
- **Results that read like a product, not a database.** Card/list results with clear primary
  metadata, inline actions (open, add to agent context, versions), and progressive disclosure for
  detail — no overwhelming column grids by default.
- **Agent-first.** The grounded chat is a **first-class panel**: select documents from results →
  ask → answers cite sources with an expandable tool-run trace + correlation id.
- **Data-driven fields.** Columns, filters, and detail panels are rendered from `GET /config`
  (neutral keys + labels + flags) — no hard-coded `customN` (see §7.2). A firm's custom fields show
  up automatically with their configured labels.
- **Accessible & responsive.** WCAG-minded, keyboard-friendly, works on smaller viewports.

**Functionality checklist:** unified search across Documents/Emails/Matters/Folders/Clients with
keyword/title/author-typist/number modes + advanced filter builder; matter/folder browse + Recent
Matters; document detail (versions, extracted text); multi-library scoping; agent chat with
context selection, citations, and tool-run trace; Connect API / Connect MCP auth flows; mock-mode
badge.

**Build notes:**
- Typed API client targeting the App Service proxy only (same-origin, private).
- Modern component system (e.g. a maintained React UI library + design tokens) so the look is
  cohesive and themeable per customer.

### 8.1 Functional UX Requirements (behaviors, not visuals)

These are the required behaviors the rebuilt SPA must support. They describe *what the interface
must do*, independent of visual styling. Each requirement is mapped through the App Service proxy
(§7) and APIM routes (§5); iManage-specific grammar is honored server-side (§3) so the UI exposes
simple controls, not raw syntax.

#### 8.1.1 Search — entity types & modes

- **Entity scope** must be selectable across **Documents, Emails, Folders, Clients, and
  Matters** (Matters surfaced as a "Recent Matters" / workspaces feed). Switching entity scope
  **retains the current search text** and, if criteria exist, re-runs the search under the new
  scope. Result-affecting state (results, selected doc, breadcrumb, matter scope, total count)
  resets on scope change.
- **Quick modes per entity:**
  - *Documents / Emails:* **Keyword** (`anywhere`, full-text, no wildcard), **Title**
    (`name`, wildcard-wrapped `*term*`), **Author/Typist** (maps to iManage `owner`, covering
    author and typist), **Number** (document number; a leading `#` is stripped). Documents
    default to `email_mode=exclude`; Emails force `email_mode=only` and send text as `anywhere`
    regardless of the selected quick tab.
  - *Matters:* **Keyword** (`anywhere`), **Title** (workspace `name`), **Owner** (shares the
    `author` key, labeled "Owner").
  - *Folders:* searched by folder **name** only (quick tabs render but only the text is used);
    a search term is **required** (empty folder searches must not execute). Document-folder vs
    email-folder sub-tabs are selectable.
  - *Clients:* searched by `query`; empty client searches must not execute.
- **Execution:** search runs **only** on explicit **Search** click, **Enter**, or a
  navigation-triggered load — **no search-as-you-type / no debounce**. Changing the search text
  or quick tab **clears displayed results immediately**. An in-flight request is
  **cancellable** (shared `AbortController`); cancellation clears loading/error state without
  surfacing an error. Starting a new request aborts the prior one.
- Within a matter scope, an **empty** search is valid (lists matter contents); otherwise search
  is disabled with no criteria.

#### 8.1.2 Advanced filter builder

- **Core fields always available:** Title, Keyword, Author, Doctype. An **"Add another field"**
  picker offers an **entity-dependent** field set:
  - *Documents/Emails:* Application, Author, Author/Typist, BCC, Body, CC, Category, Client,
    Comments, Create Date, Department, Doc. Number, Doctype, Edit Date, From, Keyword, Last User,
    Matter, Matter Lead, Received, Sent, Subclass, To, Typist, Version.
  - *Matters:* Category, Client, Create Date, Department, Description, Edit Date, Keyword, Matter,
    Matter Close Date, Matter Lead, Matter Open Date, MatterUno, Owner, Title.
  - *Folders:* Owner.
- **Operators** on text fields: **Contains** (`*value*`), **Contains Exactly** (`value`),
  **Does Not Contain** (`!value` / `NOT`). Doctype is always *contains-exactly* from a fixed
  type list (Word/Excel/PDF/PowerPoint/Email/Text/HTML + "Any Type"). Date fields are free-text
  (no required date-picker); no dedicated numeric/user-picker controls are required.
- **Combination semantics:** multiple values within one field combine as space-separated terms
  in a single parameter (AND-like); multiple fields all narrow together. **No user-facing
  AND/OR grouping, parentheses, or nested Boolean groups.**
- **Field-specific grammar (honored server-side):** Title wildcard-wraps positive values;
  Keyword uses full-text terms with `NOT <term>` negation (never `!`); Author sends positive
  values to `owner`-mapped search. **Negation that the tenant cannot express server-side (Title
  `does-not-contain`, Author `does-not-contain`) must be applied client-side** against the
  returned result fields; when client-side filtering is applied, the displayed total reflects the
  filtered local count. Author matching treats `|`-separated values as separate needles and tests
  a leading `@` both with and without it.

#### 8.1.3 Library / database scoping

- The UI must let the user **independently toggle** the configured libraries (discovered via
  `GET /config` / `GET /libraries`, §7.1 — **not hard-coded**). Selecting **all** libraries omits
  the `libraries` filter (search everything); selecting a subset sends the comma-separated list.
  Document searches pass libraries in the request body; matter/folder searches pass them as a
  query parameter. Library scoping is applied as a **single customer-level call** (no per-library
  fan-out).

#### 8.1.4 Results

- **Result rows** must show selection checkbox, Title, Version, Document Number, Edit Date, File
  Size, and Workspace Name, with **client-side sorting** on each column (first click ascending,
  re-click toggles; sorts the loaded window — no server-side sort param).
- **Result count indicator:** `1 – <loaded> of <total>` with a trailing `+` when more may exist;
  total derived from `total` / `total_count` (including nested shapes), falling back to loaded
  count.
- **Paging ladder, not offset paging:** initial page size **500**, **"Load more"** re-fetches
  from offset 0 at **5,000** (max 5,000) to preserve server relevance ordering — **no infinite
  scroll, no appended next page**. "Load more" shows only when returned count ≥ requested size
  and current size < 5,000.
- **States:** distinct **loading** ("Searching…" + Cancel), **no-search-yet** prompt,
  **zero-results** ("No Matches!"), **search-error** (shows backend error), and
  **authentication-required** ("Sign In Required" + Work API sign-in action).
- **Per-row actions:** open document (→ detail panel), open matter/folder (→ drill-in),
  **checkbox toggles the row into AI agent context** (cap **5**; header checkbox selects first 5
  sorted). A selected-documents bar exposes **Open Chat** and **Clear**. Detail provides an
  external **Open in iManage** deep link when `library` + `doc_num` exist. (No download action is
  required.)

#### 8.1.5 Browse / navigation

- **Recent Matters** is the only auto-loading feed (loads recent workspaces, limit 500, on
  entering that scope). Other entities wait for an explicit search.
- **Matter drill-down** lists direct subfolders + loose documents, pushes the matter onto a
  breadcrumb stack, and **activates matter scope** (subsequent searches restricted by
  `workspace_id`). **Folder drill-down** lists child folders + documents and pushes onto the same
  breadcrumb stack **without** enabling matter scope.
- **Breadcrumb:** root link + each opened container in root-first order; intermediate items are
  clickable to reopen; the final item is not clickable. Returning to root (or the matter-scope
  "X") clears the folder stack + matter scope and schedules a fresh search.

#### 8.1.6 Document detail

- Detail panel must provide **Properties, Preview, Versions, Security** tabs.
  - **Properties:** render only populated fields from the normalized model (name, version, doc
    number, dates, size, author/typist + description, comments, application, doctype, workspace,
    library, category, matter lead, department, client, matter, office, security). **Custom
    profile fields render dynamically** from `GET /config` (§7.2) — unmapped fields do not render.
  - **Preview / extracted text:** **Load Preview / Refresh** fetches document text via the **MCP
    `fetch` route**, reading **sequential chunks** (start index 0, **≤12 requests**, honoring
    `totalTextChunks`, stopping when complete or an empty chunk returns), updating after each
    chunk and showing a `<loaded> of <total> chunk(s)` indicator. The text parser must tolerate
    multiple response shapes (direct, JSON-RPC `result.content[].text`, JSON-encoded, recursive
    fallback) and show clear "no text" / "preview error" fallbacks.
  - **Versions:** show at minimum current version, edit date, and file size (a full version list
    is a parity-optional enhancement).
  - **Security:** show the document's default security, defaulting to "Public" when absent.

#### 8.1.7 Agent chat

- **Context selection:** up to **5** documents via row checkbox, header checkbox (first 5), or a
  detail-panel "Chat with this document" action; the selected count surfaces in the Ask-AI entry
  points. A **Clear** action empties the selection.
- **Sending:** send via button or **Enter**; **Shift+Enter** inserts a newline; send is disabled
  when blank or while a prior turn is loading; input is trimmed and the user turn is echoed
  immediately. When documents are selected, the turn first posts the **context set**
  (`selected_set` with document ids + metadata) then posts the turn to the conversation.
- **Conversation model:** a conversation id is generated per app session; turns are kept
  **in-memory** (no prior-turn reload; reload starts fresh).
- **Answer rendering:** assistant answers render as **lightweight sanitized Markdown** (bold,
  italic, inline code, `-` bullets, newlines); user messages render as plain text. Responses must
  surface **citations** (document name/id/library/confidence; name truncated for display; clicking
  a citation selects the matching doc **only if already in the loaded results**) and a **tool-run
  trace** (name, status, latency). Chat is **non-streaming** — show a "Thinking…" indicator and
  add the assistant turn once complete. Errors render **as an assistant message**, not a toast.

#### 8.1.8 Auth / connect flows

- On load and **every 5 minutes**, poll **Work API** and **MCP** auth status independently; the
  header shows `API ✓/✗`, `MCP ✓/✗`, and the authenticated user name when available.
- **Sign In** (Work missing) and **Connect MCP** (Work present, MCP missing) start the respective
  OAuth flows with a `return_to` back to the current view (interactive authorize rides the user's
  browser per §4.3). Support the **chained flow**: after a Work callback, auto-start MCP if still
  missing (and vice-versa); strip callback query params from the URL afterward.
- **Sign Out** appears only when both are connected; it logs out, clears both auth states, the
  username, and results.
- Auth is **not** globally gating — navigation/search/chat remain available and surface
  **per-action** auth-required states (e.g., a `authorization_required` search response renders
  "Sign In Required").
- **Mock/demo mode:** read a health/`GET /config` flag; when mock, show a **"Demo data"**
  indicator clarifying there is no live iManage connection.

#### 8.1.9 Cross-cutting behaviors

- **Persistence (localStorage):** **Recent searches** (≤10, dedup by entity+text, with
  entity/text/quick-filter/timestamp, "Clear all" action) and **Saved searches** (id, name,
  entity, text, quick filter, **selected libraries**, timestamp). All other state
  (advanced filters, sort, selections, chat, breadcrumb, matter scope, preview) is session-only
  and resets on reload. No cross-tab sync is required.
- **Keyboard:** Enter runs search (main box and advanced inputs, when criteria exist); Enter
  saves in the Save-Search name input; Enter sends chat; Shift+Enter newlines chat.
- **Dismissal:** Recent-searches and entity-selector dropdowns close on outside click.
- **Errors:** API errors carry `HTTP <status>: <body excerpt>`; search errors clear results and
  render a search-error state; auth errors render the sign-in state; preview errors render inline;
  chat errors render as assistant messages. (No global toast system required.)

## 9. Observability & Fine-Grained Visibility

- Log Analytics + App Insights; APIM diagnostics → per-operation request logs & custom metrics;
  Foundry diagnostics (model + agent runs). Dashboards/workbooks for: calls per iManage
  operation, per library, latency, error codes, model token usage, agent turn traces by
  correlation id. Alerts on error-rate/latency/token thresholds.

## 10. Security & Compliance (WAF Alignment)

- **Security:** Entra ID sign-in (EasyAuth) on the web app, APIM policies + subscription keys on
  each route, managed identities + RBAC (no shared keys where avoidable), secrets in Key
  Vault, token scrubbing in logs, TLS 1.2+, optional APIM JWT/IP policies.
- **Reliability:** zone-redundant SKUs where available, health checks, retry/backoff to iManage.
- **Operational excellence:** full IaC (Bicep + azd), per-route telemetry, mock mode, documented
  runbooks.
- **Performance efficiency:** single customer-level calls, NAT for stable egress, APIM caching
  where safe (non-PII metadata).
- **Cost optimization:** right-sized SKUs, per-customer stamp, optional shared Log Analytics.
- Mapped to Azure **Well-Architected Framework** pillars with a checklist.

## 11. Deliverables

**Output location:** this spec is maintained in `docs/product-spec.md`. Supporting
artifacts live under `docs/`.

1. `docs/product-spec.md` — the consolidated spec (this plan, expanded).
2. `docs/architecture/` — draw.io + mermaid diagram + narrative.
3. `docs/apim/` — fine-grained route & policy design (APIs, operations, policy XML outlines).
4. `infra/` — Bicep modules + `azure.yaml` (azd), with **managed VNet** default and
   **BYO-VNet** parameterization.
5. `mock-upstream/` — standalone **Mock iManage Upstream** service (own azd service + Bicep
   module) emulating the Work REST + MCP surfaces; serves **OpenAPI/Swagger** docs (`/docs`) so
   the API can be explored/tested directly; swappable APIM backend (`imanageBackendMode`).
6. `docs/security/` — WAF alignment + compliance checklist.
7. `docs/rollout.md` — phased epics & acceptance criteria.

> Implementation of code/IaC is a **follow-on**; this task delivers the **product spec** and
> supporting design artifacts. Build-out epics below define the roadmap.

## 12. Phased Rollout — Epics

> **Sprint 1 (current) — functionality-first, open network.** Build the four public components and
> prove the end-to-end hosted-agent↔APIM path against the mock, with the `live` iManage switch in
> place. Order: **S1.1 IaC (open) → S1.2 APIM routes/policies → S1.3 Mock iManage → S1.4 Foundry +
> hosted agent (Agent Framework) → Gate G1 (agent → APIM public /imanage/mcp → mock) → S1.5 Backend
> proxy + agent bridge → S1.6 Frontend SPA → S1.7 live-backend swap smoke.** No VNet, PE, NAT,
> or token forwarding in Sprint 1.
>
> - **S1.1 — IaC foundation (open network):** Bicep + azd for Foundry (public), APIM (public,
>   Standard v2), web App Service (public), mock App Service (public). Fresh azd env
>   `azure-imanage-dev` → RG `rg-azure-imanage-dev`.
> - **S1.2 — APIM fine-grained APIs & policies** (`/models`, `/agents`, `/imanage/work|mcp|oauth`)
>   with the **mock ↔ live backend switch**.
> - **S1.3 — Mock iManage upstream** (Work REST + MCP emulator) as the default APIM backend.
> - **S1.4 — Foundry + hosted agent (Agent Framework, Responses API, gpt-5.6-sol).**
> - **Gate G1 (Sprint 1):** hosted agent runs a model turn **and** calls the iManage MCP tool at
>   **APIM public `/imanage/mcp` → mock**, returning tool output + trace; agent model calls route
>   through APIM `/models`. (Open-network variant of the gate — no private-MCP hop.)
> - **S1.5 — Backend proxy + agent bridge;** **S1.6 — Frontend SPA;** **S1.7 — live swap smoke.**

### Sprint 2+ — Network isolation (deferred)

> **Build order (per decision):** after networking, stand up **Foundry + a hosted agent with the
> MCP tool behind the VNet and validate it end-to-end inside the VNet (Gate G1) BEFORE building
> the rest of the stack.** This de-risks the hardest integration (private MCP tool ↔ DataProxy)
> first. Sequence: **1 → 2 → 3 → 6 → G1 → 4 → 5 → 7 → 8 → 8b → 9 → 10 → 11 → 12.**

- **Epic 1 — Architecture & spec finalization:** diagrams, network topology, request/auth flows,
  deliverable docs scaffold.
- **Epic 2 — IaC foundation:** Bicep structure + azd, parameters, managed-VNet vs BYO-VNet switch.
- **Epic 3 — Networking & private connectivity:** VNet/subnets, NSGs, private endpoints, private
  DNS, NAT Gateway, + the **internal Container Apps environment** subnet that will
  host the private MCP tool.
- **Epic 6 — Foundry (VNet-injected) + hosted agent (BYO resources) + MCP tool.** Build on the
  Microsoft Foundry **"standard agent with tools behind VNet"** reference (BYO-VNet, subnet
  delegation, private endpoints, Capability Host, BYO Storage/Cosmos/Search). Deploy the iManage
  **MCP tool to an internal Container Apps environment** (native VNet routing for the DataProxy;
  Streamable HTTP + `Mcp-Session-Id`).
- **Gate G1 — Validate hosted agent in-VNet (STOP/GO):** from a host with VNet line-of-sight,
  confirm (a) the hosted agent runs a model turn, (b) it **successfully calls the private MCP
  tool** (a temporary
  stub/echo MCP is fine before real iManage) returning tool output with a tool-run trace, and
  (c) the agent's model connection **routes through APIM `/models`** so the `llm-token-limit` /
  `llm-emit-token-metric` policies **fire on agent turns** (verify a token metric is emitted and a
  deliberately low limit throttles the agent). Use **retries** to absorb the known
  `TaskCanceledException` Hyena-routing flakiness. **Do not proceed past G1 until the hosted agent
  ↔ private MCP path works and agent model calls are governed by APIM.**
  > **G1 finding (2026-10-04):** the model turn works, but the first MCP attempt failed with
  > `424 Failed Dependency` because the initial Foundry account was created **without** agent VNet
  > injection, so the DataProxy had no route to the private MCP endpoint. **Resolution:** recreate
  > the Foundry account per template 19 with `networkInjections` scenario `agent` → `snet-agents`,
  > BYO Cosmos/Storage/Search + capability host, and front the MCP tool with the internal Container
  > Apps hop. The classic agent registered during the first attempt was deleted and is being
  > rebuilt on the new agents (Responses API) surface.
- **Epic 4 — APIM Standard v2 (private) + fine-grained APIs & policies.**
- **Epic 5 — Identity & secrets:** UAMIs, RBAC, Key Vault, iManage app-reg prerequisites doc.
- **Epic 7 — iManage OAuth integration (Work + MCP) + per-user token forwarding.**
- **Epic 8 — Backend proxy incl. agent bridge + mock mode.**
- **Epic 8b — Mock iManage Upstream service** (standalone Work REST + MCP emulator; APIM
  backend-swap `imanageBackendMode`; full-stack validation with no live tenant/egress).
- **Epic 9 — Frontend SPA (modern, task-oriented UX — not an iManage-UI clone).**
- **Epic 10 — Observability & fine-grained telemetry + dashboards/alerts.**
- **Epic 11 — Security & compliance (WAF) validation.**
- **Epic 12 — CI/CD (azd), docs, functional test harness.**

## 13. Recommended Resolutions (opinionated defaults)

These resolve the previously-open decisions with concrete recommendations; each is a parameter
so a customer can override.

- **Login routing → Direct OAuth.** Both authorize and token
  exchange/refresh go **direct** to the iManage OAuth host; only the data plane (Work REST + MCP)
  is routed through APIM. *(resolved — see `docs/prereqs/imanage-oauth.md` §4.1)*
- **Agent → iManage auth → Per-user token forwarding (structured input).** The agent consumes the
  iManage MCP server through a **direct MCP tool** (`client.get_mcp_tool(name="imanage",
  url=IMANAGE_MCP_URL, headers={"Authorization": "Bearer {{imanageToken}}"}, …)`). The web app
  authorizes the user to iManage in its **own** Connect flow, then
  forwards that user's iManage bearer per request as the `imanageToken` **structured input**;
  Foundry substitutes it into the templated MCP `Authorization` header so each call runs as the
  signed-in user. APIM forwards the bearer unchanged (it never mints or rewrites tokens).
  **Why not Foundry OAuth Identity Passthrough (OBO)?** OBO requires an *interactive* consent
  handshake that only interactive hosts (the Foundry playground) can drive; over the Responses API
  the web app uses, the consent gate cannot be surfaced to the user, so the prompt never appears.
  Token forwarding needs no separate agent consent and behaves exactly like iManage's own OAuth.
  Trade-off: the user's short-lived iManage token travels as a structured input, so it must never
  be logged (enforced by the no-log-body APIM rule). *(resolved; ref: Foundry structured inputs —
  per-request MCP headers)*
- **APIM → Standard v2**, public access Disabled, inbound private endpoint, outbound VNet
  integration, zone-redundant where the region supports it.
- **App Service → Premium v3 (P1v3)** Linux Python, regional VNet integration + private
  endpoint, `httpsOnly`, FTP disabled, health check `/health`.
- **Foundry model → `gpt-5.6-sol` default** (swappable via `DEPLOYMENT_NAME`), Entra ID auth (API
  keys disabled) via managed identity.
- **Model API governance → Foundry ↔ APIM AI Gateway** managed GenAI policies (token-limit,
  token-metric, load-balancing, optional content-safety) as the baseline; **semantic caching
  disabled**. iManage Work/MCP/OAuth policies remain explicitly authored (AI Gateway covers model
  traffic only).
- **BYO agent resources → provision by default** (Storage + Cosmos DB + AI Search), all private
  endpoints; parameterized so a customer can point at existing resources.
- **Agent framework → Microsoft Agent Framework.** The chat agent is **authored with Microsoft
  Agent Framework** (sample style) but **deployed as a Foundry hosted agent** in Agent Service —
  it **does not run in the web app**. The App Service only bridges turns to it via APIM `/agents`;
  all agent reasoning, tool calls, and model inference execute in the hosted agent.
- **VNet mode → managed (stamp-created) for dev/demo/validation; BYO-VNet for enterprise prod.**
  Both use the identical private, tools-behind-VNet pattern — the only difference is who owns the
  VNet. **Managed** (default for your own builds and Gate G1): the stamp provisions the VNet +
  subnets + NSGs + private DNS, zero network prerequisites. A stamp-created VNet is **isolated**,
  so it does **not** route-conflict with other VNets unless you later peer it — just choose a
  **non-overlapping CIDR**. Watch-outs in a shared/governed subscription: subscription **Azure
  Policy** (deny-public-access, forced tags/SKUs, DINE private-DNS auto-linking to a central
  zone), **central/hub private DNS** ownership, **globally-unique resource names** (use the
  generated suffix), and **quota/region capacity**. **BYO-VNet** (recommended for enterprise):
  deploy into the customer's existing VNet + pre-created delegated subnets so it plugs into their
  hub-spoke, central DNS, ExpressRoute/VPN, and egress firewall — required when the network team
  owns connectivity/compliance. **Guidance: use a sandbox/dev subscription + managed VNet for
  validation; use BYO-VNet for customer production.**
- **Egress → NAT Gateway (stable source IP), always deployed, unrestricted by default.** NAT is a
  **standard component of every stamp** — it gives the VNet outbound to iManage SaaS and a
  predictable source IP for allow-listing (Azure retired free default outbound access Sep 2025, so
  an explicit egress method is required). It does **not** filter destinations. Destination
  filtering (Azure Firewall FQDN allow-list) is **opt-in** (`deployEgressFirewall=false` default)
  for customers with strict egress/exfiltration policies; when enabled it sits in front of the NAT
  path.
- **Regions/redundancy → single-region, zone-redundant** defaults; multi-region DR is a future epic.
- **Secrets → Key Vault with RBAC** (not access policies), via App Service KV references + APIM named values.
- **Mock iManage upstream → first-class service, `imanageBackendMode=mock|live`** (default
  `live` for prod stamps; `mock` for non-prod/CI/demo). Its own azd service + Bicep module +
  private endpoint; emulates the Work REST + MCP surfaces with a built-in fake dataset. Serves
  **OpenAPI/Swagger** docs (`/openapi.json` + Swagger UI at `/docs`) describing the emulated Work
  REST surface — doubles as the contract APIM imports for the Work API. APIM backend entity swap
  means no route/policy changes when moving mock→live.

**Remaining customer prerequisites (not decisions):** iManage tenant + Work/MCP OAuth app
registrations (redirect URIs → private App Service host), and — if BYO-VNet — an existing VNet
with the required delegated subnets.

## 14. Notes & Considerations

- Follow very clear, direct code style (no over-abstraction), consistent with Microsoft Agent
  Framework samples, when the implementation phase begins.
- On Microsoft-managed devices, use the CFS proxy feeds for pip/npm during build.
- Keep all firm-specific values out of the repo; drive via parameters/config.
