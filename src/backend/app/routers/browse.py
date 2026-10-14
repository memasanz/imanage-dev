"""Browse: libraries, recent matters, workspace/folder children, clients, users."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..config import Settings
from ..deps import client_dep, get_session, settings_dep
from ..imanage_client import ImanageClient
from ..normalize import normalize_document, normalize_library, normalize_workspace

router = APIRouter()


def _token(request: Request) -> str | None:
    session = get_session(request)
    return session.work_token if session else None


@router.get("/libraries")
async def libraries(
    request: Request, client: ImanageClient = Depends(client_dep)
) -> dict:
    rows = await client.list_libraries(_token(request))
    return {"libraries": [normalize_library(r) for r in rows]}


@router.get("/workspaces/recent")
async def recent(
    request: Request,
    client: ImanageClient = Depends(client_dep),
    settings: Settings = Depends(settings_dep),
) -> dict:
    rows = await client.recent_workspaces(_token(request))
    return {"results": [normalize_workspace(r, settings.field_map, kind="matter") for r in rows]}


@router.get("/workspaces/{ws_id}/children")
async def workspace_children(
    ws_id: str,
    request: Request,
    client: ImanageClient = Depends(client_dep),
    settings: Settings = Depends(settings_dep),
) -> dict:
    raw = await client.workspace_children(_token(request), ws_id)
    return _split_children(raw, settings)


@router.get("/folders/{folder_id}/children")
async def folder_children(
    folder_id: str,
    request: Request,
    client: ImanageClient = Depends(client_dep),
    settings: Settings = Depends(settings_dep),
) -> dict:
    raw = await client.folder_children(_token(request), folder_id)
    return _split_children(raw, settings)


def _split_children(raw: dict, settings: Settings) -> dict:
    rows = raw.get("data", raw.get("results", []))
    folders, documents = [], []
    for r in rows:
        is_folder = r.get("container_type") == "folder" or r.get("type") in ("folder", "workspace", "regular", "search")
        if is_folder:
            folders.append(normalize_workspace(r, settings.field_map, kind="folder"))
        else:
            documents.append(normalize_document(r, settings.field_map))
    # Frontend (browse drill + BrowsePanel) consumes `results`; keep folders/documents too.
    return {"results": folders + documents, "folders": folders, "documents": documents}


@router.get("/clients/search")
async def clients_search(
    q: str = "", request: Request = None, client: ImanageClient = Depends(client_dep)
) -> dict:
    rows = await client.clients_search(_token(request), q)
    return {"results": [{"id": r.get("id"), "name": r.get("name"), "type": "client"} for r in rows]}


@router.get("/users/search")
async def users_search(
    q: str = "", request: Request = None, client: ImanageClient = Depends(client_dep)
) -> dict:
    rows = await client.users_search(_token(request), q)
    return {"results": rows}


@router.get("/users/me")
async def users_me(
    request: Request, client: ImanageClient = Depends(client_dep)
) -> dict:
    return await client.users_me(_token(request))
