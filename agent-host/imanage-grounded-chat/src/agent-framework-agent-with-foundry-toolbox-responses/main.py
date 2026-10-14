# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


async def main():
    credential = DefaultAzureCredential()

    # Create the chat client
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=credential,
    )

    # iManage MCP tool — per-user OAuth, "the way iManage works".
    #
    # The agent calls the iManage MCP endpoint (IMANAGE_MCP_URL; the governed APIM
    # /imanage/mcp route in production, the mock in dev) carrying the SIGNED-IN USER'S
    # own iManage bearer token on every request. The token is supplied per request by
    # the web app as the `imanageToken` structured input and bound into the Authorization
    # header via the {{imanageToken}} handlebar placeholder — so each call runs as that
    # user, with no interactive Foundry OBO consent gate. APIM forwards the bearer
    # unchanged to iManage (it never mints or rewrites tokens). See the product spec.
    mcp_tool = client.get_mcp_tool(
        name="imanage",
        url=os.environ["IMANAGE_MCP_URL"],
        headers={"Authorization": "Bearer {{imanageToken}}"},
        approval_mode="never_require",
    )

    agent = Agent(
        client=client,
        instructions=(
            "You are the iManage AI Workspace assistant. You answer questions about the "
            "legal and business documents the user has selected in the app.\n\n"
            "Rules:\n"
            "- Only answer from the content of the selected documents. Use the iManage tools "
            "(search, fetch) to read a document's text by its id before relying on it.\n"
            "- If the selected documents do not contain the answer, say so plainly. Do not "
            "guess or use outside knowledge.\n"
            "- Always cite the specific document(s) you used, by id and name.\n"
            "- Be concise and factual. Quote short passages when precision matters.\n"
            "- You act as the signed-in user: you can only read what their iManage "
            "permissions allow."
        ),
        tools=[mcp_tool],
        # History will be managed by the hosting infrastructure, thus there
        # is no need to store history by the service. Learn more at:
        # https://developers.openai.com/api/reference/resources/responses/methods/create
        default_options={"store": False},
    )

    server = ResponsesHostServer(agent)
    await server.run_async()


if __name__ == "__main__":
    asyncio.run(main())
