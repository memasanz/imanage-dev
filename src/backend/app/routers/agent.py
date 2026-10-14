"""Agent context management + chat turns (bridged to the Foundry hosted agent)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from ..agent_bridge import run_turn
from ..config import Settings
from ..deps import client_dep, ensure_session, get_session, settings_dep
from ..imanage_client import ImanageClient

logger = logging.getLogger(__name__)

router = APIRouter()


class ContextAdd(BaseModel):
    id: str
    name: str | None = None


class TurnRequest(BaseModel):
    message: str
    document_ids: list[str] | None = None


@router.get("/context")
def get_context(request: Request) -> dict:
    session = get_session(request)
    docs = session.context_docs if session else {}
    return {"documents": [{"id": k, "name": v} for k, v in docs.items()]}


@router.post("/context")
def add_context(body: ContextAdd, request: Request, response: Response) -> dict:
    session = ensure_session(request, response)
    session.context_docs[body.id] = body.name or body.id
    return {"documents": [{"id": k, "name": v} for k, v in session.context_docs.items()]}


@router.delete("/context/{doc_id}")
def remove_context(doc_id: str, request: Request) -> dict:
    session = get_session(request)
    if session:
        session.context_docs.pop(doc_id, None)
    docs = session.context_docs if session else {}
    return {"documents": [{"id": k, "name": v} for k, v in docs.items()]}


@router.delete("/context")
def clear_context(request: Request) -> dict:
    session = get_session(request)
    if session:
        session.context_docs.clear()
    return {"documents": []}


def _user_id(request: Request) -> str | None:
    """The signed-in user's stable id for per-user OBO.

    Prefers the App Service Easy Auth principal object id (``X-MS-CLIENT-PRINCIPAL-ID``); falls
    back to the opaque session id so per-browser demos still partition per user.
    """
    oid = request.headers.get("X-MS-CLIENT-PRINCIPAL-ID")
    if oid:
        return oid
    from ..deps import SESSION_COOKIE

    return request.cookies.get(SESSION_COOKIE)


@router.post("/agent/turns")
async def agent_turn(
    body: TurnRequest,
    request: Request,
    client: ImanageClient = Depends(client_dep),
    settings: Settings = Depends(settings_dep),
) -> dict:
    session = get_session(request)
    doc_ids = body.document_ids or (list(session.context_docs) if session else [])
    mcp_token = session.mcp_token if session else None
    user_id = _user_id(request)
    message = (body.message or "").strip()
    if not message:
        return {
            "answer": "Please enter a question for the assistant.",
            "citations": [],
            "trace": [],
            "correlation_id": None,
            "error": "empty_message",
        }
    try:
        return await run_turn(settings, client, message, doc_ids, mcp_token, user_id)
    except Exception:  # noqa: BLE001 — surface a friendly error, never a 500 to the chat UI
        logger.exception("agent turn failed")
        return {
            "answer": (
                "The assistant is temporarily unavailable. Please try again in a moment."
            ),
            "citations": [],
            "trace": [],
            "correlation_id": None,
            "error": "agent_unavailable",
        }
