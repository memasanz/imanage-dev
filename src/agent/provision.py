"""Post-provision validation for the iManage agent (Responses API, ephemeral).

There is no classic agent resource to register: the agent is **ephemeral** — its definition
(instructions + iManage MCP tool) lives in the app and is passed to the Foundry project
Responses API per turn. Foundry runs the model and executes the MCP tool server-side. This
script just validates that path end-to-end after `azd provision`, from a host that can reach
the Foundry endpoint.

    pip install -r requirements.txt
    $env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
    $env:MODEL_DEPLOYMENT_NAME    = "gpt-4o"
    $env:IMANAGE_MCP_URL          = "https://<apim>/imanage/mcp"
    python provision.py
"""
from __future__ import annotations

import sys

from imanage_agent import build_client, load_spec, mcp_tool


def main() -> int:
    spec = load_spec()
    print(f"Agent (ephemeral): name={spec.name} model={spec.model}")
    print(f"  MCP tool '{spec.mcp_server_label}' -> {spec.mcp_server_url}")
    print("No persisted agent resource is created; the definition ships with the app.")

    client = build_client()
    response = client.responses.create(
        model=spec.model,
        instructions=spec.instructions,
        input="Confirm you are ready and list the iManage MCP tools you can use.",
        tools=[mcp_tool(spec)],
    )
    print(f"validation status={getattr(response, 'status', 'unknown')}")
    print(f"[assistant] {response.output_text}")
    return 0 if response.output_text else 1


if __name__ == "__main__":
    sys.exit(main())
