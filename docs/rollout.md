# Rollout — Phased Epics & Acceptance Criteria

Delivery roadmap for the open-network, per-customer iManage AI Workspace stamp. See
[`product-spec.md`](./product-spec.md). Status is tracked in the session todo store.

Legend: **D** = design artifact, **B** = build/IaC, **A** = app code.

---

## Epic 1 — Architecture & spec finalization (D) — *in progress*
**Scope:** product spec, architecture diagram (mermaid + draw.io), APIM route/policy design,
rollout doc.
**Acceptance:**
- `docs/product-spec.md`, `docs/architecture/` (README + `.mmd` + `.drawio`), `docs/apim/README.md`,
  `docs/rollout.md` exist and are internally consistent.
- Diagram shows browser → public App Service → public APIM → Foundry + iManage egress.
- All earlier decisions resolved (no open questions).

## Epic 2 — IaC foundation (B)
**Scope:** Bicep module layout + `azure.yaml` (azd); global parameters; **managed-VNet vs
BYO-VNet** switch.
**Acceptance:**
- `azd provision` validates (what-if) against an empty resource group.
- `byoVnet=false` creates the VNet; `byoVnet=true` consumes supplied subnet resource ids.
- No hardcoded firm-specific values; all via `main.parameters.json`.

## Epic 3 — Networking (B)
**Scope:** open-network posture — the web app and APIM are publicly reachable over HTTPS; the
web app gates access with Entra ID sign-in (EasyAuth). No VNet, private endpoints, private DNS,
VPN, or NAT gateway.
**Acceptance:**
- Web app + APIM reachable over public HTTPS; web app requires Entra ID sign-in.
- iManage egress works over public internet with no VNet dependency.
- A fully-private topology (VNet, private endpoints, VPN, NAT) is explicitly out of scope.

## Epic 4 — APIM Standard v2 (public) + fine-grained APIs & policies (B)
**Scope:** APIM public gateway; the 5 APIs with named operations; policies
per `docs/apim`.
**Acceptance:**
- APIM reachable via its public gateway.
- Each operation emits per-operation metrics with `api`/`operation`/`status` dimensions.
- OAuth `token` injects the client secret and logs issuance without token material.

## Epic 5 — Identity & secrets (B)
**Scope:** user-assigned managed identities, RBAC, Key Vault (private, RBAC), iManage
app-registration prerequisites doc.
**Acceptance:**
- App Service MI reads Key Vault; APIM MI authenticates to Foundry; Foundry MI has ACR/BYO access.
- No secrets in app settings — only Key Vault references / named values.
- `docs/prereqs/imanage-oauth.md` documents exact redirect URIs + required scopes.

## Epic 6 — Foundry (VNet-injected) + hosted agent (BYO resources) (B/A)
**Scope:** Foundry account/project network injection; BYO Storage/Cosmos/Search; model
deployment; hosted agent (Agent Framework) with the iManage MCP tool; validate per-user token
forwarding.
**Acceptance:**
- Foundry account public access disabled; agent runs succeed via APIM `/agents`.
- Hosted agent can call the iManage MCP tool with a forwarded per-user token and fetch document text.

## Epic 7 — iManage OAuth integration (Work + MCP) + token forwarding (A)
**Scope:** PKCE flows, per-session isolated token store, hybrid token exchange via APIM, forwarding
the per-user MCP token to the agent.
**Acceptance:**
- Two independent Connect flows (Work + MCP) complete; tokens never shared across sessions.
- Token exchange/refresh traverse APIM; agent turn runs as the user via the forwarded token.

## Epic 8 — Backend proxy + agent bridge + mock mode (A)
**Scope:** FastAPI proxy endpoints honoring the iManage grammar rules; agent bridge to Foundry via
APIM; in-process mock mode.
**Acceptance:**
- Grammar rules honored (owner vs author, title wildcarding, classic surface, library scoping, etc.).
- All upstream calls go through APIM base URL; in-process mock mode runs with no network.

## Epic 8b — Mock iManage Upstream service (A/B)
**Scope:** standalone service (own azd service + Bicep module + private endpoint) emulating the
iManage Work REST + MCP JSON-RPC surfaces with a built-in fake dataset; serves OpenAPI/Swagger
docs (`/openapi.json` + Swagger UI at `/docs`) for direct exploration/testing of the emulated
Work API; APIM backend entities `imanage-work-backend`/`imanage-mcp-backend` + `imanageBackendMode` swap.
**Acceptance:**
- With `imanageBackendMode=mock`, the full stack (App Service→APIM→agent→mock) works with
  **no internet egress** and no live tenant.
- Switching to `imanageBackendMode=live` requires **no route/policy change** — only the backend target.
- Mock responses satisfy the proxy's expectations (shapes/fields the UI consumes).
- Swagger UI (`/docs`) lists every emulated Work operation and executes against the mock dataset.

## Epic 9 — Frontend SPA (modern, task-oriented UX) (A)
**Scope:** React/Vite SPA delivering the full feature set (search with scope chips + advanced
builder, matters/folders browse, Recent Matters, doc detail/versions/text, multi-library, agent
chat with context + citations + tool-run trace, Connect flows, mock badge) in a clean modern UX.
**Acceptance:**
- Every capability in §3 is present; typed client targets the App Service proxy only (same-origin).
- UX is a fresh, task-oriented design (not an iManage-UI clone); fields render from `GET /config`.

## Epic 10 — Observability & fine-grained telemetry (B)
**Scope:** Log Analytics + App Insights; APIM/Foundry diagnostics; dashboards + alerts.
**Acceptance:**
- Dashboards show calls per iManage operation, per library, latency, token usage, agent traces.
- Alerts fire on error-rate/latency/token thresholds.

## Epic 11 — Security & compliance (WAF) validation (D/B)
**Scope:** WAF-pillar alignment checklist; access-control (Entra sign-in), token-scrubbing, RBAC review.
**Acceptance:**
- `docs/security/waf-checklist.md` complete with evidence per control.
- Access gated by Entra ID sign-in; secrets only in Key Vault; token material absent from logs.

## Epic 12 — CI/CD + docs + tests (B/A)
**Scope:** azd pipeline; product-spec/rollout docs finalized; functional test harness.
**Acceptance:**
- `azd up` deploys a working stamp end to end.
- Test harness validates iManage grammar against the mock upstream (or a live tenant).

---

## Dependency order
Epic 1 → 2 → 3 → (4, 5) → 6 → 7 → 8 → 8b → 9 → (10, 11) → 12

> Epic 8b can run in parallel with 6–7 once APIM (4) exists, and is the recommended way to
> validate Epics 7–9 before a live iManage tenant is available.
