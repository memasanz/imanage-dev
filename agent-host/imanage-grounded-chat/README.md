# iManage grounded-chat — Foundry hosted agent

The production AI agent for **iManage AI Workspace**. It is authored with the
[Microsoft Agent Framework](https://github.com/microsoft/agent-framework) and deployed as a
**Foundry hosted agent** (Responses protocol). The web app never runs the agent in‑process — it
posts each turn to this hosted agent, which reads iManage document text over MCP and returns a
grounded, cited answer.

## How it works

- **Model.** The agent uses `FoundryChatClient` (Agent Framework) against the Foundry project's
  **`gpt-5.6-sol`** deployment (see [`azure.yaml`](azure.yaml)). Model inference is governed by the
  Foundry AI Gateway → APIM.
- **iManage MCP tool (direct).** The agent attaches a single MCP tool via
  `client.get_mcp_tool(name="imanage", url=IMANAGE_MCP_URL, …)`. `IMANAGE_MCP_URL` is the governed
  **APIM `/imanage/mcp`** route in production (the mock MCP in dev). The agent discovers/invokes the
  iManage MCP `search` + `fetch` tools over MCP at runtime.
- **Per‑user identity (forward token — "the way iManage works").** Every call carries the
  **signed‑in user's own iManage bearer** in the MCP `Authorization` header, so it runs as that
  user and iManage permissions / ethical walls are enforced.
  The web app forwards that token per request as the **`imanageToken`** structured input, and the
  tool header binds it with the `{{imanageToken}}` handlebar placeholder. APIM forwards the bearer
  unchanged to iManage (it never mints or rewrites tokens). There is **no interactive Foundry OBO
  consent gate** — the user authorizes iManage once in the web app's own Connect flow. In dev/mock
  the MCP upstream accepts any token.

See [`src/.../main.py`](src/agent-framework-agent-with-foundry-toolbox-responses/main.py) for the
implementation.

## Deploy (azd)

Prerequisites: [azd ≥ 1.32](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd),
the Foundry CLI extension bundle, and `azd auth login`.

```bash
# Install the unified Foundry extensions (provides `azd ai agent`, `connection`, `toolbox`, ...)
azd ext install microsoft.foundry
azd auth login
```

The agent reads the iManage MCP endpoint from `IMANAGE_MCP_URL` (the APIM `/imanage/mcp` route in
production, the mock in dev). Before `azd up`, set the model deployment name and the MCP URL in the
azd environment, then provision and deploy:

```bash
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.6-sol
azd env set IMANAGE_MCP_URL https://<apim-host>/imanage/mcp
azd up
```

After editing the tool or agent code, redeploy:

```bash
azd deploy --all
```

## Run & invoke locally

`azd up` must run first (it provisions the model deployment + agent). Then:

```bash
azd ai agent run                       # starts the host on http://localhost:8088
azd ai agent invoke --local "..."      # invoke the local agent
azd ai agent invoke "..."              # invoke the deployed agent
```

For the full guide, see
[Deploy a hosted agent](https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent).

## Troubleshooting

- **MCP source fails the whole agent.** If the iManage MCP endpoint errors during `tools/list`,
  the agent can't load its tools and requests return HTTP 500 until it recovers. Retry (usually
  transient), or verify `IMANAGE_MCP_URL` / APIM `/imanage/mcp` is reachable, then `azd deploy --all`.
- **Authorization errors on tool calls.** The tool acts as the signed‑in user via the forwarded
  `imanageToken`; if that token is missing/expired or the user lacks access to the iManage document,
  the call fails even though the tool was discovered and invoked correctly. Confirm the web app
  Connect iManage flow completed so the user's bearer is present.
- **Inspect deployed logs:** `azd ai agent monitor`.

## Related

- Solution overview and iManage MCP requirements/tools: [`../../README.md`](../../README.md)
- APIM `/imanage/mcp` route + policies: [`../../docs/apim/README.md`](../../docs/apim/README.md)
- iManage OAuth (Work + MCP) setup: [`../../docs/prereqs/imanage-oauth.md`](../../docs/prereqs/imanage-oauth.md)
