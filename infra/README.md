# Infrastructure (Bicep + azd)

IaC for the open-network, per-customer **iManage AI Workspace** stamp. See
[`../docs/product-spec.md`](../docs/product-spec.md) and [`../docs/rollout.md`](../docs/rollout.md).

## What the stamp deploys (Sprint 1 — open network)

`main.bicep` (subscription scope) creates the resource group and calls `resources.bicep`, which
deploys only what the customer does **not** bring:

```
infra/
  main.bicep              # subscription-scope orchestrator: creates the RG, deploys the stamp
  resources.bicep         # resource-group-scope: wires the stamp modules
  main.parameters.json    # azd parameter bindings (env-var substitution)
  abbreviations.json      # resource-name abbreviations
  modules/
    monitoring.bicep      # Log Analytics + Application Insights
    identity.bicep        # user-assigned managed identity for the App Services
    webapp-public.bicep   # web App Service (FastAPI proxy + React SPA) and the mock upstream
    apim-config.bicep     # registers the iManage Work + MCP routes/policies onto the BYO APIM
```

**Bring-your-own (referenced via `.env`, not created):** the Azure AI Foundry project + model
deployment, and the customer's API Management instance. Foundry model/agent traffic is
governed through the BYO APIM via the Foundry AI Gateway; the stamp only registers the iManage
**Work** + **MCP** routes on that APIM.

**Network posture:** every resource has public network access — no VNet, private endpoint, VPN,
or NAT gateway. Configure and verify **Entra ID sign-in** (App Service Authentication /
EasyAuth) before allowing access to non-demo data; do not treat this stamp as a production
security baseline.

## Deploy

```bash
# Configure your own azd environment using the root .env.example first.
azd provision     # deploy/update the stamp (also registers the APIM Work + MCP routes)
azd deploy web    # ship the web app (FastAPI proxy + React SPA)
azd up            # provision + deploy in one step
```

Switching the iManage backend from the mock upstream to a real tenant is a backend-target + auth
change, not an API/policy edit — see [`../docs/apim/traffic-routing.md`](../docs/apim/traffic-routing.md) §5.

## Status

- **Sprint 1 (open network): done** — orchestrator + stamp (observability, identity, web + mock
  App Services, BYO APIM route registration). Both compile via `az bicep build`.
- Models/Agents route through the BYO APIM via the Foundry AI Gateway; iManage Work + MCP routes
  are registered by `apim-config.bicep`.

## Deferred (Sprint 2 — private networking)

The `modules/` folder also carries an **unwired blueprint** for the fully-private target topology
— `network.bicep`, `nat.bicep`, `privatedns.bicep`, `keyvault.bicep`, `apim.bicep`,
`apim-api.bicep`, `appservice.bicep`, and `foundry.bicep` (Foundry agent VNet injection). These
are **not deployed by the active open-network stamp**; they stage the Sprint 2 design described in
[`../docs/product-spec.md`](../docs/product-spec.md) §4 (VNet + subnets, private endpoints, private
DNS, NAT egress, and a private MCP path). The hosted agent's **private MCP tool** requires Foundry
**agent VNet injection**, which is set **only at account creation** and cannot be retrofitted.
