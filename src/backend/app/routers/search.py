"""Search across entity types, honoring iManage grammar server-side.

The SPA sends neutral keys + simple modes; this router builds the iManage query (owner vs
author, title wildcarding, number search, email vs document, library scoping) so the UI never
deals with raw syntax.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..config import Settings
from ..deps import client_dep, get_session, settings_dep
from ..imanage_client import ImanageClient
from ..normalize import (
    filters_to_imanage,
    normalize_document,
    normalize_workspace,
)

router = APIRouter()


class SearchRequest(BaseModel):
    entity: str = "documents"
    mode: str = "keyword"
    text: str = ""
    libraries: list[str] | None = None
    filters: list[dict] | None = None
    page: int = 1
    page_size: int = 25


def _work_token(request: Request) -> str | None:
    session = get_session(request)
    return session.work_token if session else None


def _build_document_query(req: SearchRequest, settings: Settings) -> dict:
    body: dict = {}
    text = (req.text or "").strip()

    if req.mode == "title":
        body["title"] = f"*{text}*" if text else "*"
    elif req.mode == "author":
        body["owner"] = text  # Author/Typist maps to owner; name/email resolved to id in search().
    elif req.mode == "number":
        body["document_number"] = text
    else:  # keyword
        if text:
            body["anywhere"] = text

    body["filters"] = filters_to_imanage(req.filters or [], settings.field_map)

    if req.entity == "emails":
        body["email_only"] = True
        body["group_by_conversation"] = False
    else:
        body["exclude_emails"] = True

    libs = req.libraries or settings.imanage_libraries
    if libs:
        body["libraries"] = ",".join(libs)

    body["limit"] = req.page_size
    body["offset"] = (req.page - 1) * req.page_size
    return body


async def _resolve_owner_id(client: ImanageClient, token: str | None, text: str) -> str | None:
    """Resolve an author/typist name or email to an iManage user id.

    iManage matches ``owner`` by user id, so a typed display name ("Morgan Rivera") must be
    looked up via users/search first. Prefers an exact id/name/email match, then a name
    substring match, then the first result. Returns ``None`` if nothing matches.
    """
    try:
        users = await client.users_search(token, text)
    except Exception:  # noqa: BLE001 — resolution is best-effort; fall back to the raw term
        return None
    needle = text.strip().lower()
    for user in users:
        if needle in {str(user.get(key, "")).lower() for key in ("id", "name", "email", "full_name")}:
            return user.get("id")
    for user in users:
        if needle in str(user.get("name", "")).lower():
            return user.get("id")
    return users[0].get("id") if users else None


@router.post("/search")
async def search(
    req: SearchRequest,
    request: Request,
    client: ImanageClient = Depends(client_dep),
    settings: Settings = Depends(settings_dep),
) -> dict:
    token = _work_token(request)
    field_map = settings.field_map

    if req.entity in ("documents", "emails"):
        body = _build_document_query(req, settings)
        if req.mode == "author" and (req.text or "").strip():
            owner_id = await _resolve_owner_id(client, token, req.text.strip())
            if owner_id:
                body["owner"] = owner_id
        raw = await client.search_documents(token, body)
        rows = raw.get("data", raw.get("results", []))
        total = raw.get("total", len(rows))
        results = [normalize_document(r, field_map) for r in rows]
    elif req.entity == "matters":
        rows = await client.recent_workspaces(token)
        results = [normalize_workspace(r, field_map, kind="matter") for r in rows]
        total = len(results)
    elif req.entity == "folders":
        rows = await client.folders_search(token, req.text)
        results = [normalize_workspace(r, field_map, kind="folder") for r in rows]
        total = len(results)
    elif req.entity == "clients":
        rows = await client.clients_search(token, req.text)
        results = [{"id": r.get("id"), "name": r.get("name"), "type": "client"} for r in rows]
        total = len(results)
    else:
        results, total = [], 0

    return {
        "total": total,
        "page": req.page,
        "page_size": req.page_size,
        "results": results,
    }
