from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..config import Settings
from ..deps import get_session, settings_dep

router = APIRouter()


@router.get("/health")
def health(request: Request, settings: Settings = Depends(settings_dep)) -> dict:
    session = get_session(request)
    return {
        "status": "ok",
        "mode": settings.imanage_backend_mode,
        "work_connected": bool(session and session.work_token),
        "mcp_connected": bool(session and session.mcp_token),
    }


@router.get("/config")
def config(settings: Settings = Depends(settings_dep)) -> dict:
    fields = [
        {
            "key": e.key,
            "label": e.label,
            "searchable": e.searchable,
            "filterable": e.filterable,
            "show_in_detail": e.show_in_detail,
        }
        for e in settings.field_map
    ]
    return {
        "mode": settings.imanage_backend_mode,
        "fields": fields,
        "entities": ["documents", "emails", "folders", "clients", "matters"],
        "features": {"agent": True},
    }
