"""HTTP client for the iManage upstream.

All upstream traffic goes through APIM whenever APIM_BASE_URL is set — in both mock and live
mode. APIM fronts the mock upstream (mock) or real iManage (live), so every Work REST and MCP
call is visible in APIM. Only local dev with no APIM configured talks to the mock upstream
directly. Surface base URLs are the only difference, so routers stay identical.
"""
from __future__ import annotations

from typing import Any

import httpx

from .config import Settings


class UpstreamError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


class ImanageClient:
    def __init__(self, settings: Settings):
        self.s = settings
        # Route through APIM whenever it's configured (both mock and live), so every call is
        # logged by APIM. Fall back to the mock upstream directly only for local dev.
        self.via_apim = bool(settings.apim_base_url)
        self.cid = settings.imanage_customer_id

    # --- base URLs per surface --------------------------------------------
    @property
    def _work_base(self) -> str:
        if self.via_apim:
            return f"{self.s.apim_base_url}/imanage/work/customers/{self.cid}"
        return f"{self.s.mock_upstream_url}/work/api/v2/customers/{self.cid}"

    @property
    def _mcp_base(self) -> str:
        if self.via_apim:
            return f"{self.s.apim_base_url}/imanage/mcp"
        return f"{self.s.mock_upstream_url}/mcp"

    def _headers(self, token: str | None, mcp: bool = False) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        if token:
            # Work expects X-Auth-Token; MCP expects an OAuth bearer. The APIM per-API policy
            # checks for the matching header and fails closed (401) if it's missing.
            if mcp:
                h["Authorization"] = f"Bearer {token}"
            else:
                h["X-Auth-Token"] = token
        if self.via_apim and self.s.apim_subscription_key:
            h["Ocp-Apim-Subscription-Key"] = self.s.apim_subscription_key
        return h

    async def _get(self, url: str, token: str | None, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url, headers=self._headers(token), params=params)
        return self._json(r)

    async def _post(self, url: str, token: str | None, json: dict, mcp: bool = False) -> Any:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(url, headers=self._headers(token, mcp=mcp), json=json)
        return self._json(r)

    @staticmethod
    def _json(r: httpx.Response) -> Any:
        if r.status_code >= 400:
            raise UpstreamError(r.status_code, f"upstream {r.status_code}")
        return r.json()

    # --- Work REST ---------------------------------------------------------
    async def list_libraries(self, token: str | None) -> list[dict]:
        data = await self._get(f"{self._work_base}/libraries", token)
        return data.get("data", data.get("libraries", []))

    async def search_documents(self, token: str | None, payload: dict) -> dict:
        return await self._post(f"{self._work_base}/documents/search", token, payload)

    async def get_document(self, token: str | None, doc_id: str) -> dict:
        data = await self._get(f"{self._work_base}/documents/{doc_id}", token)
        return data.get("data", data)

    async def get_versions(self, token: str | None, doc_id: str) -> list[dict]:
        data = await self._get(f"{self._work_base}/documents/{doc_id}/versions", token)
        return data.get("data", data.get("versions", []))

    async def get_text(self, token: str | None, doc_id: str) -> str:
        data = await self._get(f"{self._work_base}/documents/{doc_id}/text", token)
        return data.get("text", "")

    async def recent_workspaces(self, token: str | None) -> list[dict]:
        data = await self._get(f"{self._work_base}/workspaces", token, {"recent": "true"})
        return data.get("data", data.get("results", []))

    async def workspace_children(self, token: str | None, ws_id: str) -> dict:
        return await self._get(f"{self._work_base}/workspaces/{ws_id}/children", token)

    async def folder_children(self, token: str | None, folder_id: str) -> dict:
        return await self._get(f"{self._work_base}/folders/{folder_id}/children", token)

    async def clients_search(self, token: str | None, q: str) -> list[dict]:
        data = await self._get(f"{self._work_base}/clients/search", token, {"q": q})
        return data.get("data", data.get("results", []))

    async def folders_search(self, token: str | None, q: str) -> list[dict]:
        data = await self._get(f"{self._work_base}/folders/search", token, {"q": q})
        return data.get("data", data.get("results", []))

    async def users_search(self, token: str | None, q: str) -> list[dict]:
        data = await self._get(f"{self._work_base}/users/search", token, {"q": q})
        return data.get("data", data.get("results", []))

    async def users_me(self, token: str | None) -> dict:
        data = await self._get(f"{self._work_base}/users/me", token)
        return data.get("data", data)

    # --- MCP (JSON-RPC) ----------------------------------------------------
    async def mcp_fetch_text(self, token: str | None, doc_id: str) -> str:
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "fetch", "arguments": {"id": doc_id}},
        }
        data = await self._post(self._mcp_base, token, body, mcp=True)
        result = data.get("result", {})
        content = result.get("content") or []
        if content and isinstance(content, list):
            return content[0].get("text", "")
        return result.get("text", "")
