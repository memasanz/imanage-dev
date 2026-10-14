# Proxy API Contract (App Service ↔ SPA)

The SPA talks **only** to the App Service proxy (same-origin, private). The proxy fronts APIM
routes and normalizes iManage responses to **neutral** shapes (§7.2 of the product spec). This
contract is the single source of truth shared by the backend (Epics 7/8) and frontend (Epic 9).

Base path: `/api`. All responses JSON. Auth is cookie/session based (per-browser session).

## Config & health

- `GET /api/health` → `{ "status": "ok", "mode": "mock" | "live", "work_connected": bool, "mcp_connected": bool }`
- `GET /api/config` → UI contract:
  ```json
  {
    "mode": "mock",
    "fields": [
      { "key": "client", "label": "Client", "searchable": true, "filterable": true, "show_in_detail": true }
    ],
    "entities": ["documents", "emails", "folders", "clients", "matters"],
    "features": { "agent": true }
  }
  ```

## Auth (per-session, two independent connects)

- `GET  /api/auth/status` → `{ "work": bool, "mcp": bool }`
- `GET  /api/auth/work/start` → 302 to iManage authorize (browser follows)
- `GET  /api/auth/work/callback?code=…&state=…` → sets session, 302 back to SPA
- `GET  /api/auth/mcp/start`, `GET /api/auth/mcp/callback` → same for MCP
- `POST /api/auth/logout` → clears session

## Search

- `POST /api/search` →
  ```json
  {
    "entity": "documents",            // documents|emails|folders|clients|matters
    "mode": "keyword",                // keyword|title|author|number
    "text": "merger agreement",
    "libraries": ["ACTIVE_US"],       // optional; omitted = all
    "filters": [                      // advanced builder; neutral keys only
      { "key": "client", "op": "is", "value": "412117" }
    ],
    "page": 1, "page_size": 25
  }
  ```
  Response:
  ```json
  {
    "total": 134,
    "page": 1, "page_size": 25,
    "results": [
      {
        "id": "ACTIVE_US!1234.1",
        "type": "document",
        "name": "Merger Agreement",
        "extension": "docx",
        "version": 3,
        "author": { "id": "jsmith", "text": "Jane Smith" },
        "fields": { "client": { "id": "412117", "text": "Acme Corp" } },
        "updated_at": "2026-09-01T12:00:00Z"
      }
    ]
  }
  ```

## Browse

- `GET /api/workspaces/recent` → `{ "results": [ { "id", "name", "fields": {…} } ] }`
- `GET /api/workspaces/{id}/children` → folders + documents under a workspace/folder
- `GET /api/folders/{id}/children` → same shape
- `GET /api/libraries` → `{ "libraries": [ { "id": "ACTIVE_US", "name": "Active (US)" } ] }`
- `GET /api/clients/search?q=…`, `GET /api/users/search?q=…`, `GET /api/users/me`

## Document detail

- `GET /api/documents/{id}` → full neutral document (fields, author, class, versions count)
- `GET /api/documents/{id}/versions` → `{ "versions": [ { "version", "updated_at", "size" } ] }`
- `GET /api/documents/{id}/text` → `{ "text": "…", "source": "mcp" | "work", "truncated": bool }`

## Agent context + chat

- `GET    /api/context` → `{ "documents": [ { "id", "name" } ] }`
- `POST   /api/context` `{ "id": "ACTIVE_US!1234.1" }` → add selected doc
- `DELETE /api/context/{id}` → remove; `DELETE /api/context` → clear
- `POST   /api/agent/turns` →
  ```json
  { "message": "Summarize the indemnification terms", "document_ids": ["ACTIVE_US!1234.1"] }
  ```
  Streaming or non-streaming response:
  ```json
  {
    "answer": "…grounded answer…",
    "citations": [ { "id": "ACTIVE_US!1234.1", "name": "Merger Agreement" } ],
    "trace": [ { "tool": "imanage-mcp.fetch", "args": {…}, "ms": 420 } ],
    "correlation_id": "c-abc123"
  }
  ```

## Error shape

All errors: `{ "error": { "code": "string", "message": "human readable", "correlation_id": "…" } }`
with the appropriate HTTP status. Tokens are never returned or logged.
