# iManage agent (Foundry Responses API)

> **Reference implementation, not the active web app integration.** The web app invokes the
> hosted agent in [`../../agent-host/imanage-grounded-chat/`](../../agent-host/imanage-grounded-chat/).
> The private-network probes below describe the deferred topology; they are not needed for
> the local mock quickstart.

The grounded-chat agent that answers from the user's selected documents, as the signed-in
user. It runs on the **Foundry project Responses API** as an **ephemeral agent**: its
definition (instructions + iManage MCP tool) ships with the app, while **Foundry** performs
model inference and executes the MCP tool **server-side, inside the VNet-injected agent
subnet**. The MCP tool reaches iManage through APIM (`/imanage/mcp`), so every tool call is
proxied and logged there.

This is the **new agents surface** (Responses API), not the classic threads/runs Assistants
API. There is no persisted agent resource to register.

## Files

- `imanage_agent.py` — the agent definition (name, grounding instructions, model, iManage MCP
  tool) + a small Responses client helper. Single source of truth.
- `provision.py` — post-provision validation: runs one Responses turn with the MCP tool to
  confirm the end-to-end path. Creates **no** agent resource.
- `g1_model_only.py` — Gate G1 model-only probe (inference, no tool).
- `g1_smoke.py` — Gate G1 end-to-end (model + private iManage MCP tool through APIM).
- `requirements.txt` — OpenAI SDK + Entra identity.

## How it fits

- The web app **does not** run the agent. `src/backend/app/agent_bridge.py` calls the Foundry
  project Responses API per turn, forwarding the user's short-lived iManage MCP token as the
  `imanageToken` structured input; the agent binds it into the MCP tool's `Authorization: Bearer
  {{imanageToken}}` header (per-user token forwarding, never logged).
- The MCP tool executes server-side in Foundry's injected subnet — which is what clears the
  424 that a non-injected account hits when reaching private APIM.

## Validate (run at Gate G1)

Run from a host that can reach the Foundry endpoint. Auth is
Microsoft Entra ID only — Foundry API keys are disabled.

```powershell
pip install -r requirements.txt
$env:FOUNDRY_PROJECT_ENDPOINT = "<foundry projectEndpoint output>"
$env:MODEL_DEPLOYMENT_NAME    = "gpt-4o"
$env:IMANAGE_MCP_URL          = "<apimGatewayUrl output>/imanage/mcp"
python g1_model_only.py   # inference only
python g1_smoke.py        # inference + private MCP tool through APIM
```

The web app needs only `FOUNDRY_PROJECT_ENDPOINT` and `MODEL_DEPLOYMENT_NAME` (set by IaC);
no `AGENT_ID` is required.
