"""Agent bridge — forwards a chat turn to the Foundry **hosted agent**.

The agent does NOT run in this web app. The web app only submits the turn; a Microsoft Agent
Framework agent **hosted in Foundry** performs model inference and executes the iManage MCP
tool (via its Foundry Toolbox) server-side. The web app POSTs to the hosted agent's
OpenAI-compatible Responses endpoint:

    {foundry_project_endpoint}/agents/{foundry_agent_name}/endpoint/protocols/openai/responses

Auth is a Microsoft Entra ID bearer token (scope ``https://ai.azure.com/.default``) obtained
from the web app's managed identity. The hosted agent owns its model, instructions, and tools,
so the web app sends only the user's message plus the selected-document context — no model,
instructions, or tool wiring travels from the web app.

Per-user iManage auth ("the way iManage works"): the web app authenticates to Foundry with
its **own** workload token (managed identity, scope ``https://ai.azure.com/.default``) to invoke
the agent, and forwards the **signed-in user's** own iManage bearer as the ``imanageToken``
structured input. The hosted agent binds that token into its iManage MCP ``Authorization`` header
(``{{imanageToken}}``), so every tool call runs as that user.
APIM forwards the bearer unchanged to iManage (it never mints or rewrites tokens). There is
no interactive Foundry OBO consent gate. (In mock/dev the MCP upstream accepts any token.)

``_obo_headers`` additionally conveys the user's object id (``x-ms-user-identity``) for per-user
log/data partitioning. The ``_consent_*`` helpers remain only as a defensive fallback for a
legacy OBO-connection deployment; with forward-token they are never exercised.

When no Foundry agent is configured (local/dev), a deterministic grounded stub is returned so
the app is demoable end-to-end without Foundry.
"""
from __future__ import annotations

import re
import uuid

from .config import Settings
from .imanage_client import ImanageClient

# Markers the Foundry toolbox / Agent Service use when a user must consent to the iManage
# OAuth2 connection. Two shapes exist:
#   1. JSON-RPC tool error (older toolbox): code ``-32006`` + ``CONSENT_REQUIRED``.
#   2. Responses output item (current Agent Service): ``type: oauth_consent_request`` carrying a
#      ``consent_link`` to the Azure consent page (``*.consent.azure-apim.net``).
_CONSENT_CODE = "-32006"
_CONSENT_MARKERS = ("CONSENT_REQUIRED", "oauth_consent_request", "OAuth consent required", _CONSENT_CODE)
_CONSENT_URL_RE = re.compile(r"https://[^\s\"'<>]*consent[^\s\"'<>]*", re.IGNORECASE)


async def run_turn(
    settings: Settings,
    client: ImanageClient,
    message: str,
    document_ids: list[str],
    mcp_token: str | None,
    user_id: str | None = None,
) -> dict:
    correlation_id = f"c-{uuid.uuid4().hex[:12]}"

    if settings.foundry_project_endpoint and settings.foundry_agent_name:
        return await _run_hosted_agent(
            settings, message, document_ids, mcp_token, user_id, correlation_id
        )
    return await _run_stub(client, message, document_ids, mcp_token, correlation_id)


def _hosted_agent_base_url(settings: Settings) -> str:
    """OpenAI-compatible Responses base for the hosted agent. Prefer the governed APIM
    `/agents` route when configured, else derive it from the project endpoint + agent name."""
    if settings.agent_responses_base_url:
        return settings.agent_responses_base_url.rstrip("/")
    endpoint = settings.foundry_project_endpoint.rstrip("/")
    return f"{endpoint}/agents/{settings.foundry_agent_name}/endpoint/protocols/openai"


def _obo_headers(settings: Settings, user_id: str | None, mcp_token: str | None) -> dict:
    """Headers that convey the signed-in user's identity for per-user OBO passthrough."""
    headers: dict[str, str] = {}
    mode = settings.agent_obo_mode
    if mode in ("middle_tier", "auto") and user_id:
        headers[settings.agent_user_identity_header] = user_id
    if mode in ("forward_token", "auto") and mcp_token:
        headers[settings.agent_forward_mcp_token_header] = mcp_token
    return headers


async def _run_hosted_agent(
    settings: Settings,
    message: str,
    document_ids: list[str],
    mcp_token: str | None,
    user_id: str | None,
    correlation_id: str,
) -> dict:
    """POST the turn to the Foundry hosted agent's Responses endpoint.

    The web app's managed identity supplies the workload bearer; per-user identity travels in
    OBO headers (see ``_obo_headers``). Imports are lazy so the backend (and its tests) run
    without the OpenAI SDK in mock/dev.
    """
    from azure.identity import DefaultAzureCredential
    from openai import AsyncOpenAI

    credential = DefaultAzureCredential()
    token = credential.get_token(settings.foundry_token_scope).token

    default_headers = {"x-correlation-id": correlation_id}
    default_headers.update(_obo_headers(settings, user_id, mcp_token))

    openai = AsyncOpenAI(
        base_url=_hosted_agent_base_url(settings),
        api_key=token,
        default_query={"api-version": "v1"},
        default_headers=default_headers,
    )

    context_note = (
        "Selected document ids for this question: " + ", ".join(document_ids)
        if document_ids
        else "No documents selected."
    )

    # Per-user iManage auth, "the way iManage works": forward the signed-in user's own
    # iManage bearer to the hosted agent as the `imanageToken` structured input. The agent
    # binds it into the iManage MCP Authorization header ({{imanageToken}}) so every tool
    # call runs as that user — no interactive Foundry OBO consent gate.
    create_kwargs: dict = {
        "model": settings.foundry_agent_name,
        "input": f"{context_note}\n\n{message}",
    }
    if mcp_token:
        create_kwargs["extra_body"] = {"structured_inputs": {"imanageToken": mcp_token}}

    try:
        response = await openai.responses.create(**create_kwargs)
    except Exception as exc:  # noqa: BLE001 — a consent gate surfaces as an API error
        consent_url = _consent_url_from_text(str(exc))
        if consent_url:
            return _consent_response(consent_url, correlation_id)
        raise

    consent_url = _consent_url_from_response(response)
    if consent_url:
        return _consent_response(consent_url, correlation_id)

    answer = _output_text(response)
    trace = _tool_trace(response)
    citations = [{"id": doc_id, "name": doc_id} for doc_id in document_ids]
    return {
        "answer": answer,
        "citations": citations,
        "trace": trace,
        "correlation_id": correlation_id,
    }


def _consent_response(consent_url: str, correlation_id: str) -> dict:
    """A turn result that asks the UI to have the user connect iManage (first-use OBO consent)."""
    return {
        "answer": (
            "To answer using your iManage documents, please connect iManage once. "
            "Use the Connect iManage link, then ask your question again."
        ),
        "citations": [],
        "trace": [],
        "correlation_id": correlation_id,
        "needs_consent": True,
        "consent_url": consent_url,
    }


def _consent_url_from_text(text: str) -> str | None:
    """Return a consent URL if the text looks like a toolbox consent gate (either shape)."""
    if not text:
        return None
    if not any(marker in text for marker in _CONSENT_MARKERS):
        return None
    match = _CONSENT_URL_RE.search(text)
    return match.group(0) if match else None


def _consent_url_from_response(response) -> str | None:
    """Scan a Responses payload for a toolbox consent gate.

    Prefers the structured ``oauth_consent_request`` output item (current Agent Service), then
    falls back to a raw-text scan for the older JSON-RPC ``CONSENT_REQUIRED`` tool error.
    """
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", "") == "oauth_consent_request":
            link = getattr(item, "consent_link", None)
            if link:
                return link
    try:
        raw = response.model_dump_json()
    except Exception:  # noqa: BLE001 — fall back to str() for non-pydantic payloads
        raw = str(response)
    return _consent_url_from_text(raw)


def _output_text(response) -> str:
    """Extract the assistant text from a Responses payload (SDK convenience or raw output)."""
    text = getattr(response, "output_text", "") or ""
    if text:
        return text
    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", "") != "message":
            continue
        for block in getattr(item, "content", []) or []:
            if getattr(block, "type", "") == "output_text":
                parts.append(getattr(block, "text", "") or "")
    return "".join(parts)


def _tool_trace(response) -> list[dict]:
    """Summarize MCP tool calls the agent made, for the UI's tool-run trace."""
    trace: list[dict] = []
    for item in getattr(response, "output", []) or []:
        item_type = getattr(item, "type", "")
        if item_type in ("mcp_call", "tool_call"):
            trace.append(
                {
                    "tool": getattr(item, "name", "imanage-mcp"),
                    "server_label": getattr(item, "server_label", "imanage"),
                    "status": getattr(item, "status", "completed"),
                }
            )
    return trace


async def _run_stub(
    client: ImanageClient,
    message: str,
    document_ids: list[str],
    mcp_token: str | None,
    correlation_id: str,
) -> dict:
    import time

    trace = []
    citations = []
    snippets = []
    for doc_id in document_ids:
        start = time.perf_counter()
        try:
            text = await client.mcp_fetch_text(mcp_token, doc_id)
        except Exception:
            text = await client.get_text(mcp_token, doc_id)
        ms = int((time.perf_counter() - start) * 1000)
        trace.append({"tool": "imanage-mcp.fetch", "args": {"id": doc_id}, "ms": ms})
        citations.append({"id": doc_id, "name": doc_id})
        if text:
            snippets.append(text[:600])

    grounded = "\n\n".join(snippets)
    answer = (
        f"(dev agent) Based on {len(document_ids)} selected document(s), here is what I found "
        f"relevant to \"{message}\":\n\n{grounded}"
        if grounded
        else "(dev agent) No document context was available to ground an answer. "
        "Select one or more documents and ask again."
    )
    return {
        "answer": answer,
        "citations": citations,
        "trace": trace,
        "correlation_id": correlation_id,
    }
