# iManage AI Workspace - Foundry hosted agent (Microsoft Agent Framework).
#
# The agent is grounded in the documents the signed-in user selected in the web
# app. It reads document text through the iManage MCP server, which is exposed
# to the agent as a Foundry Toolbox (a managed MCP connection).
#
# On-behalf-of: the toolbox's iManage MCP connection is configured for OAuth
# Identity Passthrough. Foundry prompts each user to sign in to iManage once,
# then securely stores and refreshes that user's token and injects it on every
# tool call - so the agent reads only what the user's iManage permissions allow.
# No token-forwarding code lives here: the platform owns the OBO exchange.
import asyncio
import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import FoundryToolbox, ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

INSTRUCTIONS = """\
You are the iManage AI Workspace assistant. You answer questions about the legal
and business documents the user has selected in the app.

Rules:
- Only answer from the content of the selected documents. Use the iManage tools
  to read a document's text by its id before relying on it.
- If the selected documents do not contain the answer, say so plainly. Do not
  guess or use outside knowledge.
- Always cite the specific document(s) you used, by id and name.
- Be concise and factual. Quote short passages when precision matters.
- You act as the signed-in user: you can only read what their iManage
  permissions allow.
"""


async def main() -> None:
    credential = DefaultAzureCredential()

    # FoundryToolbox resolves the toolbox endpoint from the environment
    # (TOOLBOX_ENDPOINT, or FOUNDRY_PROJECT_ENDPOINT + TOOLBOX_NAME), authenticates
    # every request with the credential, and forwards the platform per-request
    # call-id. The iManage MCP connection inside the toolbox is configured for
    # OAuth Identity Passthrough, so Foundry injects each user's iManage token.
    toolbox = FoundryToolbox(credential)

    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=credential,
    )

    agent = Agent(
        client=client,
        instructions=INSTRUCTIONS,
        tools=toolbox,
        # History is managed by the hosting infrastructure, so the service does
        # not need to store it.
        default_options={"store": False},
    )

    server = ResponsesHostServer(agent)
    await server.run_async()


if __name__ == "__main__":
    asyncio.run(main())
