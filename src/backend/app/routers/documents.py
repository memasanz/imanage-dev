"""Document detail: profile, versions, extracted text (MCP primary, Work API fallback)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..config import Settings
from ..deps import client_dep, get_session, settings_dep
from ..imanage_client import ImanageClient
from ..normalize import normalize_document

router = APIRouter()


def _work_token(request: Request) -> str | None:
    session = get_session(request)
    return session.work_token if session else None


def _mcp_token(request: Request) -> str | None:
    session = get_session(request)
    return session.mcp_token if session else None


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    request: Request,
    client: ImanageClient = Depends(client_dep),
    settings: Settings = Depends(settings_dep),
) -> dict:
    raw = await client.get_document(_work_token(request), doc_id)
    return normalize_document(raw, settings.field_map)


@router.get("/documents/{doc_id}/versions")
async def get_versions(
    doc_id: str, request: Request, client: ImanageClient = Depends(client_dep)
) -> dict:
    versions = await client.get_versions(_work_token(request), doc_id)
    return {"versions": versions}


@router.get("/documents/{doc_id}/text")
async def get_text(
    doc_id: str, request: Request, client: ImanageClient = Depends(client_dep)
) -> dict:
    # MCP is the primary text source; fall back to the Work API /text surface.
    mcp_token = _mcp_token(request)
    source = "mcp"
    text = ""
    if mcp_token:
        try:
            text = await client.mcp_fetch_text(mcp_token, doc_id)
        except Exception:
            text = ""
    if not text:
        source = "work"
        text = await client.get_text(_work_token(request), doc_id)
    truncated = len(text) > 20000
    return {"text": text[:20000], "source": source, "truncated": truncated}
