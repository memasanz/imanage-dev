# iManage API Traffic Routing Through APIM

How the web app's iManage **Work REST** and **MCP** calls flow through API Management, why they
must, and how to switch the backend from the mock upstream to a real iManage tenant. This is the
operational companion to the design in [`README.md`](./README.md).

## 1. Request path

```
Browser (SPA)
  -> App Service web app  (FastAPI proxy, /api/*)
     -> APIM  (your instance)      <-- every upstream call is logged here
        -> iManage upstream         (mock upstream in mock mode, real tenant in live mode)
```

The SPA only ever calls the web app's own `/api/*` endpoints (same origin). The web app's
`ImanageClient` is the component that makes the outbound call, and it is what must target APIM so
the call shows up in APIM metrics/logs.

## 2. When the proxy uses APIM

`ImanageClient` (`src/backend/app/imanage_client.py`) routes through APIM **whenever
`APIM_BASE_URL` is set** — in both `mock` and `live` mode:

| `APIM_BASE_URL` | Work base | MCP base |
|---|---|---|
| set (Azure, mock or live) | `{APIM_BASE_URL}/imanage/work/customers/{cid}` | `{APIM_BASE_URL}/imanage/mcp` |
| empty (local dev) | `{MOCK_UPSTREAM_URL}/work/api/v2/customers/{cid}` | `{MOCK_UPSTREAM_URL}/mcp` |

`IMANAGE_BACKEND_MODE` (`mock` \| `live`) no longer decides whether to use APIM — it only reflects
which upstream APIM is pointed at and whether the OAuth connect flow is real. In Azure,
`resources.bicep` always sets `APIM_BASE_URL` to the APIM gateway, so **all** deployed traffic
goes through APIM. Local dev with no APIM talks to the mock upstream directly.

### Auth headers

The proxy forwards the caller's iManage identity; APIM never mints tokens.

| Surface | Header sent by proxy | Checked by APIM policy |
|---|---|---|
| Work | `X-Auth-Token: <token>` | fails closed (401) if missing |
| MCP | `Authorization: Bearer <token>` | fails closed (401) if missing |

In mock mode the token is the stub `mock-work-token` / `mock-mcp-token` (the mock upstream accepts
any token). In live mode it is a real iManage OAuth token from the PKCE connect flow.

## 3. APIM routes

Both APIs live on your BYO APIM instance and share the
`imanage-work-mcp.xml` policy (subscription key to backend, caller-bearer passthrough,
per-operation logging, retry).

| API id | Path | serviceUrl (mock) | serviceUrl (live) |
|---|---|---|---|
| `imanage-work` | `imanage/work` | `{mock}/work/api/v2` | `https://{tenant}.cloudimanage.com/work/api/v2` |
| `imanage-mcp` | `imanage/mcp` | `{mock}/mcp` | `https://{tenant}.cloudimanage.com/mcp` |

`imanage-work` operations (one per upstream call, so each is individually visible in metrics):
`libraries`, `documents-search`, `document-get`, `document-versions`, `document-text`,
`workspaces-recent`, `workspace-children`, `folder-children`, `clients-search`, `users-search`,
`users-me`.

IaC source of truth: `infra/modules/apim-config.bicep` (registers both APIs) wired from
`infra/resources.bicep`, which computes the serviceUrls:

```bicep
var imanageWorkUrl = isMock ? 'https://${mockAppName}.azurewebsites.net/work/api/v2' : imanageWorkUrlLive
var imanageMcpUrl  = isMock ? 'https://${mockAppName}.azurewebsites.net/mcp'          : imanageMcpUrlLive
```

## 4. Registering / updating the routes

Preferred (keeps IaC as source of truth, no drift):

```bash
azd provision     # (re)registers imanage-work + imanage-mcp on the BYO APIM
azd deploy web    # ships the proxy build that calls APIM
```

Imperative (CLI, add routes to a running APIM without a full provision) — deploys just the APIM
module scoped to the APIM's resource group:

```powershell
$mock = "https://<mock-app>.azurewebsites.net"
$apimResourceGroup = "<your-apim-resource-group>"
$apimName = "<your-apim-service-name>"
az deployment group create `
  --resource-group $apimResourceGroup `
  --name add-imanage-work-route `
  --template-file infra\modules\apim-config.bicep `
  --parameters apimName=$apimName `
               imanageMcpUrl="$mock/mcp" `
               imanageWorkUrl="$mock/work/api/v2"
```

Verify:

```powershell
az apim api show --resource-group $apimResourceGroup --service-name $apimName --api-id imanage-work `
  --query "{path:path, serviceUrl:serviceUrl}" -o json
az apim api operation list --resource-group $apimResourceGroup --service-name $apimName --api-id imanage-work `
  --query "[].{op:name, method:method, url:urlTemplate}" -o table
```

## 5. Switching the backend from mock to real iManage

The API serviceUrl is the switch, but three things must line up — don't hand-edit only the
serviceUrl, or every call returns 401 (tokens would still be mock):

1. **Point the backend at the tenant.** Set `imanageWorkUrlLive` / `imanageMcpUrlLive` to
   `https://{tenant}.cloudimanage.com/...`.
2. **Turn on real OAuth.** Set `IMANAGE_BACKEND_MODE=live` so the connect flow does a real PKCE
   login and produces genuine iManage tokens (the proxy forwards them; APIM does not mint them).
3. **Use the real customer id.** Set `IMANAGE_CUSTOMER_ID` to the tenant's customer id (not `1`).

Egress to `cloudimanage.com` goes out over the public internet from the BYO APIM gateway (the
open-network stamp has no VNet integration or NAT gateway).

```bash
azd env set IMANAGE_BACKEND_MODE live
# set imanageWorkUrlLive / imanageMcpUrlLive / IMANAGE_CUSTOMER_ID for the tenant
azd provision     # updates serviceUrl on both APIs
azd deploy web
```

Routes, operations, and policies are identical in both modes — mock→live is a backend-target +
auth change, not an API/policy edit.
