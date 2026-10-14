from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field

from .data import CHILDREN_BY_PARENT, CLIENTS, DOCUMENTS, FOLDERS, LIBRARIES, ME, TEXTS, USERS, VERSIONS, WORKSPACES
from .oauth import router as oauth_router, token_is_valid

app = FastAPI(
    title="Mock iManage Upstream",
    summary="Standalone mock iManage Work REST and MCP upstream",
    version="0.1.0",
    description="Emulates selected classic iManage Work REST endpoints and a simple iManage MCP JSON-RPC surface with in-memory fake data.",
)

app.include_router(oauth_router)

# When true, the mock MCP surface rejects calls that lack a valid mock OAuth token --
# use it to visibly prove the hosted agent's OBO token is flowing through APIM.
REQUIRE_MCP_AUTH = os.getenv("MOCK_REQUIRE_MCP_AUTH", "false").lower() in ("1", "true", "yes")


class DocumentSearchRequest(BaseModel):
    keyword: str | None = None
    anywhere: str | None = None
    title: str | None = None
    number: str | None = None
    document_number: str | None = None
    owner: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    profile: dict[str, Any] = Field(default_factory=dict)
    libraries: list[str] | str | None = None
    exclude_emails: bool | None = None
    email_only: bool | None = None
    group_by_conversation: bool | None = None
    page: int | None = None
    page_size: int | None = None
    limit: int | None = None
    offset: int | None = None


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


def _auth(_: str | None = Header(default=None, alias="X-Auth-Token")) -> None:
    return None


def _doc_by_id(doc_id: str) -> dict[str, Any]:
    for doc in DOCUMENTS:
        if doc["id"] == doc_id:
            return doc
    raise HTTPException(status_code=404, detail=f"Document '{doc_id}' was not found")


def _library_filter(libraries: str | None, body_libraries: list[str] | str | None = None) -> set[str] | None:
    raw: list[str] = []
    if libraries:
        raw.extend(part.strip() for part in libraries.split(",") if part.strip())
    if body_libraries:
        if isinstance(body_libraries, str):
            raw.extend(part.strip() for part in body_libraries.split(",") if part.strip())
        else:
            raw.extend(body_libraries)
    return set(raw) if raw else None


def _text_blob(doc: dict[str, Any]) -> str:
    fields = " ".join(str(doc.get(key, "")) for key in ["name", "document_number", "author_description", "class_description", "custom1", "custom1_description", "custom2", "custom2_description", "custom3_description", "custom4_description"])
    return f"{fields} {TEXTS.get(doc['id'], '')}".lower()


def _matches_term(doc: dict[str, Any], value: str | None, *, title_only: bool = False) -> bool:
    if not value:
        return True
    term = value.replace("*", "").strip().lower()
    if not term:
        return True
    haystack = doc["name"].lower() if title_only else _text_blob(doc)
    return term in haystack


def _matches_filters(doc: dict[str, Any], request: DocumentSearchRequest) -> bool:
    filters = {**request.profile, **request.filters}
    if request.owner:
        filters["owner"] = request.owner
    if "author" in filters and "owner" not in filters:
        filters["owner"] = filters["author"]

    for key, expected in filters.items():
        if expected is None or expected == "":
            continue
        if isinstance(expected, list):
            accepted = {str(item).lower() for item in expected}
            if str(doc.get(key, "")).lower() not in accepted:
                return False
            continue
        if str(doc.get(key, "")).lower() != str(expected).lower():
            return False
    return True


def _search_documents(request: DocumentSearchRequest, libraries: str | None, exclude_emails: bool, email_only: bool) -> list[dict[str, Any]]:
    allowed_libraries = _library_filter(libraries, request.libraries)
    number = request.document_number or request.number
    keyword = request.keyword or request.anywhere
    negated = False
    if keyword and keyword.strip().upper().startswith("NOT "):
        negated = True
        keyword = keyword.strip()[4:].strip()

    matches: list[dict[str, Any]] = []
    for doc in DOCUMENTS:
        if allowed_libraries and doc["library"] not in allowed_libraries:
            continue
        if exclude_emails and doc["is_email"]:
            continue
        if email_only and not doc["is_email"]:
            continue
        if number and doc["document_number"] != str(number):
            continue
        if not _matches_filters(doc, request):
            continue
        if request.title and not _matches_term(doc, request.title, title_only=True):
            continue
        keyword_match = _matches_term(doc, keyword, title_only=False)
        if keyword and ((not negated and not keyword_match) or (negated and keyword_match)):
            continue
        matches.append(doc)
    return sorted(matches, key=lambda d: d["updated_at"], reverse=True)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mock-imanage-upstream"}


@app.get("/work/api/v2/customers/{cid}/libraries", tags=["iManage Work"])
def list_libraries(cid: str, x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    return {"data": LIBRARIES, "libraries": LIBRARIES, "total_count": len(LIBRARIES)}


@app.post("/work/api/v2/customers/{cid}/documents/search", tags=["iManage Work"])
def search_documents(
    cid: str,
    request: DocumentSearchRequest,
    libraries: str | None = Query(default=None, description="Comma-separated library ids, e.g. ACTIVE_US,EU_WORK"),
    exclude_emails: bool = Query(default=False),
    email_only: bool = Query(default=False),
    group_by_conversation: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    x_auth_token: str | None = Header(default=None, alias="X-Auth-Token"),
) -> dict[str, Any]:
    _auth(x_auth_token)
    del cid, group_by_conversation
    exclude_emails = exclude_emails or bool(request.exclude_emails)
    email_only = email_only or bool(request.email_only)
    page = request.page or page
    page_size = request.page_size or request.limit or page_size
    if request.offset is not None and request.limit:
        page = (request.offset // request.limit) + 1
    matches = _search_documents(request, libraries, exclude_emails, email_only)
    start = (page - 1) * page_size
    data = matches[start : start + page_size]
    return {"data": data, "results": data, "total_count": len(matches), "total": len(matches), "page": page, "page_size": page_size}


@app.get("/work/api/v2/customers/{cid}/documents/{doc_id:path}/versions", tags=["iManage Work"])
def get_document_versions(cid: str, doc_id: str, x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    _doc_by_id(doc_id)
    versions = VERSIONS.get(doc_id, [])
    return {"data": versions, "versions": versions, "total_count": len(versions)}


@app.get("/work/api/v2/customers/{cid}/documents/{doc_id:path}/text", tags=["iManage Work"])
def get_document_text(cid: str, doc_id: str, x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    _doc_by_id(doc_id)
    return {"id": doc_id, "text": TEXTS[doc_id], "source": "work", "truncated": False}


@app.get("/work/api/v2/customers/{cid}/documents/{doc_id:path}/download", tags=["iManage Work"])
def download_document(cid: str, doc_id: str, x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> PlainTextResponse:
    _auth(x_auth_token)
    _doc_by_id(doc_id)
    return PlainTextResponse(TEXTS[doc_id], media_type="text/plain")


@app.get("/work/api/v2/customers/{cid}/documents/{doc_id:path}", tags=["iManage Work"])
def get_document(cid: str, doc_id: str, x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    return _doc_by_id(doc_id)


@app.get("/work/api/v2/customers/{cid}/workspaces", tags=["iManage Work"])
def list_workspaces(cid: str, q: str | None = Query(default=None), libraries: str | None = Query(default=None), x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    allowed = _library_filter(libraries)
    term = (q or "").lower()
    data = [w for w in WORKSPACES if (not allowed or w["library"] in allowed) and (not term or term in w["name"].lower() or term in w["custom1_description"].lower() or term in w["custom2_description"].lower())]
    return {"data": data, "results": data, "total_count": len(data)}


@app.get("/work/api/v2/customers/{cid}/workspaces/{workspace_id:path}/children", tags=["iManage Work"])
def get_workspace_children(cid: str, workspace_id: str, x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    data = CHILDREN_BY_PARENT.get(workspace_id, [])
    return {"data": data, "children": data, "total_count": len(data)}


@app.get("/work/api/v2/customers/{cid}/folders/{folder_id:path}/children", tags=["iManage Work"])
def get_folder_children(cid: str, folder_id: str, type: str | None = Query(default=None), x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    data = CHILDREN_BY_PARENT.get(folder_id, [])
    if type:
        allowed_types = {part.strip() for part in type.split(",") if part.strip()}
        data = [child for child in data if child.get("type") in allowed_types or child.get("container_type") == "document"]
    return {"data": data, "children": data, "total_count": len(data)}


@app.get("/work/api/v2/customers/{cid}/folders/search", tags=["iManage Work"])
def search_folders(cid: str, q: str | None = Query(default=None), keyword: str | None = Query(default=None), libraries: str | None = Query(default=None), x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    allowed = _library_filter(libraries)
    term = (q or keyword or "").lower()
    data = [
        {**folder, "type": "folder", "library": folder["id"].split("!", 1)[0]}
        for folder in FOLDERS
        if (not term or term in folder["name"].lower())
        and (not allowed or folder["id"].split("!", 1)[0] in allowed)
    ]
    return {"data": data, "results": data, "total_count": len(data)}


@app.get("/work/api/v2/customers/{cid}/clients/search", tags=["iManage Work"])
def search_clients(cid: str, q: str | None = Query(default=None), keyword: str | None = Query(default=None), x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    term = (q or keyword or "").lower()
    data = [client for client in CLIENTS if not term or term in client["id"].lower() or term in client["name"].lower()]
    return {"data": data, "results": data, "total_count": len(data)}


@app.get("/work/api/v2/customers/{cid}/users/search", tags=["iManage Work"])
def search_users(cid: str, q: str | None = Query(default=None), keyword: str | None = Query(default=None), x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    term = (q or keyword or "").lower()
    data = [user for user in USERS if not term or term in user["id"].lower() or term in user["name"].lower() or term in user["email"].lower()]
    return {"data": data, "results": data, "total_count": len(data)}


@app.get("/work/api/v2/customers/{cid}/users/me", tags=["iManage Work"])
def get_me(cid: str, x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> dict[str, Any]:
    _auth(x_auth_token)
    return ME


def _rpc_result(request: JsonRpcRequest, result: Any, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": request.id, "result": result}, headers=headers or {})


def _rpc_error(request: JsonRpcRequest, code: int, message: str) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": request.id, "error": {"code": code, "message": message}}, status_code=200)


@app.post("/mcp", tags=["iManage MCP"])
def mcp(request: JsonRpcRequest, authorization: str | None = Header(default=None), mcp_session_id: str | None = Header(default=None, alias="Mcp-Session-Id")) -> JSONResponse:
    if REQUIRE_MCP_AUTH and request.method not in ("initialize",) and not token_is_valid(authorization):
        # 401 with a resource-metadata pointer is the MCP OAuth challenge real clients expect.
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request.id, "error": {"code": -32001, "message": "Unauthorized: valid iManage OAuth token required"}},
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer resource_metadata="/.well-known/oauth-protected-resource/mcp/search"'},
        )
    if request.method == "initialize":
        session_id = mcp_session_id or f"mock-{uuid.uuid4()}"
        return _rpc_result(
            request,
            {
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": "mock-imanage-upstream", "version": "0.1.0"},
                "capabilities": {"tools": {"listChanged": False}},
            },
            headers={"Mcp-Session-Id": session_id},
        )

    if request.method.startswith("notifications/"):
        # MCP notifications (e.g. notifications/initialized) are fire-and-forget: no response body.
        return JSONResponse(None, status_code=202)

    if request.method == "tools/list":
        return _rpc_result(
            request,
            {
                "tools": [
                    {
                        "name": "search",
                        "description": "Search mock iManage documents by keyword/title and optional libraries.",
                        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "libraries": {"type": "array", "items": {"type": "string"}}, "limit": {"type": "integer"}}},
                    },
                    {
                        "name": "fetch",
                        "description": "Fetch extracted text for a mock iManage document id.",
                        "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
                    },
                ]
            },
        )

    if request.method == "tools/call":
        name = request.params.get("name")
        args = request.params.get("arguments") or {}
        if name == "search":
            search_request = DocumentSearchRequest(keyword=args.get("query") or args.get("keyword"), title=args.get("title"), filters=args.get("filters") or {}, libraries=args.get("libraries"))
            matches = _search_documents(search_request, None, exclude_emails=False, email_only=False)[: int(args.get("limit", 10))]
            lines = [f"{doc['id']} | {doc['name']} | {doc['custom1_description']} / {doc['custom2_description']}" for doc in matches]
            return _rpc_result(request, {"content": [{"type": "text", "text": "\n".join(lines)}], "structuredContent": {"results": matches}, "isError": False})
        if name == "fetch":
            doc_id = args.get("id") or args.get("document_id")
            if not doc_id:
                return _rpc_error(request, -32602, "fetch requires arguments.id")
            try:
                doc = _doc_by_id(doc_id)
            except HTTPException:
                return _rpc_error(request, -32004, f"Document '{doc_id}' was not found")
            text = TEXTS[doc_id]
            return _rpc_result(request, {"content": [{"type": "text", "text": text}], "structuredContent": {"id": doc_id, "name": doc["name"], "text": text}, "isError": False})
        return _rpc_error(request, -32601, f"Unknown tool '{name}'")

    return _rpc_error(request, -32601, f"Unknown method '{request.method}'")
