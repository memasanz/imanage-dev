"""Normalize raw iManage shapes into the neutral shapes the SPA consumes (api-contract.md).

iManage returns profile fields as code+description pairs (customN + customN_description,
author + author_description, class + class_description). The SPA never sees raw customN:
each mapped field collapses to { "<key>": { "id": <code>, "text": <description> } }.
"""
from __future__ import annotations

from typing import Any

from .config import FieldMapEntry


def _pair(raw: dict, value_from: str, label_from: str) -> dict | None:
    value = raw.get(value_from)
    if value is None:
        return None
    return {"id": value, "text": raw.get(label_from) or value}


def neutral_fields(raw: dict, field_map: list[FieldMapEntry]) -> dict[str, Any]:
    """Resolve every mapped field's code + description into one neutral object."""
    out: dict[str, Any] = {}
    for entry in field_map:
        pair = _pair(raw, entry.value_from, entry.label_from)
        if pair is not None:
            out[entry.key] = pair
    return out


def normalize_document(raw: dict, field_map: list[FieldMapEntry]) -> dict:
    return {
        "id": raw.get("id"),
        "type": "email" if raw.get("is_email") else "document",
        "name": raw.get("name") or raw.get("document_name"),
        "extension": raw.get("extension"),
        "version": raw.get("version"),
        "document_number": raw.get("document_number"),
        "size": raw.get("size") or raw.get("file_size"),
        "author": _pair(raw, "author", "author_description"),
        "class": _pair(raw, "class", "class_description"),
        "workspace_id": raw.get("workspace_id"),
        "workspace_name": raw.get("workspace_name"),
        "fields": neutral_fields(raw, field_map),
        "updated_at": raw.get("edit_date") or raw.get("update_date") or raw.get("updated_at"),
        "created_at": raw.get("create_date") or raw.get("created_at"),
    }


def normalize_workspace(raw: dict, field_map: list[FieldMapEntry], kind: str = "matter") -> dict:
    return {
        "id": raw.get("id"),
        "type": kind,
        "name": raw.get("name"),
        "fields": neutral_fields(raw, field_map),
    }


def normalize_library(raw: dict) -> dict:
    return {"id": raw.get("id"), "name": raw.get("name") or raw.get("id")}


def filters_to_imanage(filters: list[dict], field_map: list[FieldMapEntry]) -> dict:
    """Translate neutral filter keys back to iManage customN codes for the query."""
    by_key = {e.key: e for e in field_map}
    out: dict[str, Any] = {}
    for f in filters or []:
        entry = by_key.get(f.get("key"))
        if entry is None:
            continue
        out[entry.value_from] = f.get("value")
    return out
