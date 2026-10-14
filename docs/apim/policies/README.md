# APIM Policy Outlines

Reference policy XML for each scope described in [`../README.md` §3](../README.md). These are
**design outlines** — concrete, readable starting points for the Bicep/azd implementation, not
final production policy. Named values in `{{double-brace}}` are Key Vault-backed or config
parameters (see [`../README.md` §4](../README.md)).

Apply order (APIM evaluates outer→inner): **global → product/API → operation**.

| File | Scope | Applies to |
|---|---|---|
| [`global.xml`](./global.xml) | All APIs | correlation id, CORS, metrics, header scrubbing |
| [`models-agents.xml`](./models-agents.xml) | Models + Agents APIs | **deltas** on the Foundry↔APIM AI Gateway baseline (correlation id, custom dims, forwarded-token run-turn); no semantic caching |
| [`imanage-work-mcp.xml`](./imanage-work-mcp.xml) | iManage Work + MCP APIs | subscription key, caller-bearer passthrough, per-op logging, retry, NAT egress |
| [`imanage-oauth.xml`](./imanage-oauth.xml) | iManage OAuth API | Key Vault client-secret injection, redirect-uri allow-list, event-only logging |

> **Swappable backend.** Work/MCP target the APIM **backend entities** `imanage-work-backend` /
> `imanage-mcp-backend`, which resolve to the mock upstream (`mock`) or the live iManage tenant
> (`live`) via `imanageBackendMode`. The policies below are identical in both modes.
