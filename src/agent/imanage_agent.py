"""Definition of the iManage grounded-chat agent + a small Responses helper.

Single source of truth for *what* the agent is: its name, grounding instructions, the model
it runs on, and the iManage MCP tool it uses to read documents as the signed-in user.

The agent runs as an **ephemeral agent on the Foundry project Responses API**: its definition
lives here (and in the web app's agent bridge) and ships with the app, while Foundry performs
model inference and executes the MCP tool **server-side, inside the VNet-injected agent
subnet**. The MCP tool's URL is the APIM `/imanage/mcp` route, so every tool call is proxied
and logged there. This is the new agents surface (Responses API), not the classic
threads/runs Assistants API.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

AGENT_NAME = "imanage-grounded-chat"

INSTRUCTIONS = """\
You are the iManage AI Workspace assistant. You answer questions about legal and business
documents that the user has selected in the app.

Rules:
- Only answer from the content of the selected documents. Use the iManage MCP `fetch` tool to
  read a document's text by its id before relying on it.
- If the selected documents do not contain the answer, say so plainly. Do not guess or use
  outside knowledge.
- Always cite the specific document(s) you used, by id and name.
- Be concise and factual. Quote short passages when precision matters.
- You act as the signed-in user: you can only read what their iManage permissions allow.
"""

# AAD scope for the Foundry (AI Services) data plane. The Responses data plane expects the
# ai.azure.com audience (a cognitiveservices-scoped token is rejected with 401/wrong-audience).
FOUNDRY_TOKEN_SCOPE = "https://ai.azure.com/.default"


@dataclass(frozen=True)
class AgentSpec:
    name: str
    model: str
    instructions: str
    mcp_server_label: str
    mcp_server_url: str


def load_spec() -> AgentSpec:
    """Build the agent spec from environment (set by the Foundry/APIM deployment outputs)."""
    return AgentSpec(
        name=os.environ.get("AGENT_NAME", AGENT_NAME),
        model=os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o"),
        instructions=INSTRUCTIONS,
        mcp_server_label="imanage",
        # APIM fine-grained MCP route — all tool calls are proxied + logged here.
        mcp_server_url=os.environ["IMANAGE_MCP_URL"],
    )


def responses_base_url() -> str:
    """OpenAI-compatible Responses base for the Foundry project endpoint."""
    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
    return f"{endpoint}/openai/v1"


def build_client():
    """An OpenAI client pointed at the Foundry project Responses endpoint, Entra-authed.

    Lazy imports so importing this module doesn't require the SDK to be installed.
    """
    from azure.identity import DefaultAzureCredential
    from openai import OpenAI

    token = DefaultAzureCredential().get_token(FOUNDRY_TOKEN_SCOPE).token
    return OpenAI(base_url=responses_base_url(), api_key=token)


def mcp_tool(spec: AgentSpec, mcp_token: str | None = None) -> dict:
    """The iManage MCP tool definition, optionally carrying a per-user OBO token.

    The APIM `/imanage/mcp` route (and iManage MCP itself) authenticates with an OAuth
    bearer in the `Authorization` header — not the Work API's `X-Auth-Token`.
    """
    return {
        "type": "mcp",
        "server_label": spec.mcp_server_label,
        "server_url": spec.mcp_server_url,
        "require_approval": "never",
        "headers": {"Authorization": f"Bearer {mcp_token}"} if mcp_token else {},
    }
