# Well-Architected Framework — Alignment & Security Checklist

How the stamp maps to the five Azure Well-Architected pillars, with the concrete control each
item is implemented by. Items marked **G1** are verified during the Gate G1 live validation.

## Security

| Control | Implemented by | Status |
|---|---|---|
| Access gated by Entra ID sign-in | App Service Authentication (EasyAuth, Entra ID) on the web app | ✅ |
| APIM reachable via public gateway | APIM Std v2 public gateway; subscription keys + policies on each route | ✅ IaC |
| Foundry auth via Entra ID (no keys) | AI Services account `disableLocalAuth=true`; managed identities only | ✅ IaC |
| No local/shared keys where avoidable | Foundry `disableLocalAuth=true`; managed identities for App Service/APIM; Key Vault RBAC (not access policies) | ✅ IaC |
| Secrets never in source | Key Vault (private endpoint); APIM named values; App Service Key Vault references | ✅ IaC |
| iManage tokens scrubbed from logs | APIM outbound policy deletes `X-Auth-Token`/`Authorization`/subscription key; backend never logs tokens | ✅ policy + code |
| Forwarded iManage token is a structured input, never a header/log | Agent bridge passes the short-lived token as the `imanageToken` structured input | ✅ code |
| TLS 1.2+ everywhere | App Service `minTlsVersion=1.2`, `httpsOnly`; APIM https-only APIs | ✅ IaC |
| Optional JWT / IP allow-list at APIM | policy hooks available (off by default) | ⚙️ optional |

## Reliability

| Control | Implemented by | Status |
|---|---|---|
| Health checks | App Service `healthCheckPath=/api/health` | ✅ IaC |
| Retry/backoff to iManage | backend httpx client + APIM | ⚙️ tune at G1 |
| Zone redundancy (APIM/App Service) where region supports | SKU selection (Std v2 / P1v3) | ⚙️ region-dependent |

## Operational Excellence

| Control | Implemented by | Status |
|---|---|---|
| Full IaC + repeatable deploy | Bicep + azd (`azure.yaml`, `infra/`) | ✅ |
| Open-network stamp (no VNet/VPN) | `resources.bicep` (webapp-public + apim-config) | ✅ |
| Per-route / per-operation telemetry | APIM fine-grained operations + `emit-metric`; App Insights | ✅ IaC / policy |
| Mock mode for demos/validation | `IMANAGE_BACKEND_MODE=mock` + mock upstream App Service | ✅ (tested locally) |
| Prereqs documented | `docs/prereqs/imanage-oauth.md` | ✅ |

## Performance Efficiency

| Control | Implemented by | Status |
|---|---|---|
| Single customer-level iManage calls (no client fan-out) | backend query builder | ✅ code |
| Direct public egress to iManage | APIM outbound over public internet | ✅ |
| Per-project model TPM/quota governance | Foundry AI Gateway → APIM (per-project) | **G1** |

## Cost Optimization

| Control | Implemented by | Status |
|---|---|---|
| Right-sized SKUs | P1v3 web / B1 mock / Std v2 APIM / S0 Foundry | ✅ IaC |
| Per-customer stamp (no shared blast radius) | one deployment per tenant | ✅ |

## Gate G1 — live validation checklist

Run against a mock-mode provision before building further confidence:

1. Agent runs a model turn (model reachable through APIM).
2. Agent calls the iManage MCP tool and returns grounded text.
3. Model inference routes **through APIM** with the token-governance policy firing (confirm
   per-project metrics in App Insights).
4. Confirm the hosted agent reaches APIM and the iManage MCP route end-to-end.
