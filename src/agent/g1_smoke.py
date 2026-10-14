"""Gate G1 — end-to-end: model + private iManage MCP tool through APIM.

Runs one grounded turn with the iManage MCP tool whose `server_url` is the APIM
`/imanage/mcp` route. Foundry executes the tool server-side from the VNet-injected agent
subnet — which is what clears the 424. Prints the reply and any MCP tool calls.

    pip install -r requirements.txt
    $env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
    $env:MODEL_DEPLOYMENT_NAME    = "gpt-4o"
    $env:IMANAGE_MCP_URL          = "https://<apim>/imanage/mcp"
    $env:PROMPT                   = "List the iManage tools you can use."   # optional
    python g1_smoke.py
"""
from __future__ import annotations

import os
import sys

from imanage_agent import build_client, load_spec, mcp_tool

spec = load_spec()
prompt = os.environ.get("PROMPT", "List the iManage MCP tools you can use, then stop.")
mcp_token = os.environ.get("IMANAGE_MCP_TOKEN")  # optional OBO token for a real tenant

client = build_client()
response = client.responses.create(
    model=spec.model,
    instructions=spec.instructions,
    input=prompt,
    tools=[mcp_tool(spec, mcp_token)],
)

print(f"status={getattr(response, 'status', 'unknown')}")

tool_calls = [
    item for item in (getattr(response, "output", []) or [])
    if getattr(item, "type", "") in ("mcp_call", "mcp_list_tools", "tool_call")
]
for item in tool_calls:
    print(f"  tool={getattr(item, 'name', getattr(item, 'type', '?'))} "
          f"status={getattr(item, 'status', 'completed')}")

print(f"[assistant] {response.output_text}")

ok = getattr(response, "status", "") in ("completed", "") and bool(response.output_text)
sys.exit(0 if ok else 1)
