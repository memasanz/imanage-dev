"""Application settings.

All values come from environment variables (App Service application settings in Azure,
`.env` locally). Nothing firm-specific is hard-coded; the field map is supplied per tenant.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FieldMapEntry:
    """One neutral field mapped to an iManage profile field (code + description pair)."""

    def __init__(self, raw: dict):
        self.key: str = raw["key"]
        self.source: str = raw["source"]
        self.value_from: str = raw.get("value_from", raw["source"])
        self.label_from: str = raw.get("label_from", f"{raw['source']}_description")
        self.label: str = raw.get("label") or raw["key"]
        self.searchable: bool = raw.get("searchable", False)
        self.filterable: bool = raw.get("filterable", False)
        self.show_in_detail: bool = raw.get("show_in_detail", True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # mock = APIM/upstream serve mock iManage data; live = real iManage. In both modes, when
    # apim_base_url is set, all upstream calls are routed through APIM (so they are logged there).
    imanage_backend_mode: Literal["mock", "live"] = "mock"

    # Base URL of APIM. When set, ALL upstream calls (Work REST + MCP) go through APIM, in both
    # mock and live mode. Left empty only for local dev, where we call mock_upstream_url directly.
    apim_base_url: str = ""
    apim_subscription_key: str = ""
    mock_upstream_url: str = "http://localhost:8080"

    # iManage tenant config (non-secret).
    imanage_customer_id: str = "1"
    imanage_libraries_raw: str = Field(default="", alias="IMANAGE_LIBRARIES")
    imanage_field_map_raw: str = Field(default="[]", alias="IMANAGE_FIELD_MAP")

    # iManage OAuth (Work + MCP). Secrets come from Key Vault references in Azure.
    work_auth_url: str = ""
    work_token_url: str = ""
    work_client_id: str = ""
    work_client_secret: str = ""
    mcp_auth_url: str = ""
    mcp_token_url: str = ""
    mcp_client_id: str = ""
    mcp_client_secret: str = ""
    oauth_redirect_base: str = "http://localhost:8000"

    # Foundry HOSTED agent. The agent runs in Foundry (not in this web app): it owns its own
    # model, instructions, and the iManage MCP toolbox (OBO via OAuth Identity Passthrough).
    # When foundry_project_endpoint + foundry_agent_name are set, the bridge POSTs the turn to
    # the hosted agent's OpenAI-compatible Responses endpoint; otherwise it runs the dev stub.
    foundry_project_endpoint: str = ""
    foundry_agent_name: str = ""
    model_deployment_name: str = "gpt-4o"

    # Optional override: full Responses base URL for the hosted agent (e.g. the governed APIM
    # `/agents` route). When empty, the base is derived from the project endpoint + agent name:
    #   {foundry_project_endpoint}/agents/{foundry_agent_name}/endpoint/protocols/openai
    agent_responses_base_url: str = ""

    # AAD scope for the Foundry (AI Services) data plane.
    foundry_token_scope: str = "https://ai.azure.com/.default"

    # Per-user OBO to the hosted agent. The web app always authenticates to Foundry with its own
    # workload token (managed identity), then conveys the *signed-in user's* identity so the
    # Foundry toolbox does per-user iManage OAuth passthrough — not the shared app identity.
    #   middle_tier   — send only x-ms-user-identity: <user oid> (documented path).
    #   forward_token — send only the user's already-held iManage MCP token.
    #   auto          — send both signals (default); whichever the toolbox honors wins.
    agent_obo_mode: Literal["middle_tier", "forward_token", "auto"] = "auto"
    # Header carrying the end-user object id for Foundry per-user context resolution.
    agent_user_identity_header: str = "x-ms-user-identity"
    # Header carrying the user's iManage MCP token for the agent-code passthrough fallback.
    agent_forward_mcp_token_header: str = "x-imanage-mcp-token"

    session_secret: str = "dev-secret-change-me"

    @property
    def imanage_libraries(self) -> list[str]:
        raw = (self.imanage_libraries_raw or "").strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                return [str(x) for x in json.loads(raw)]
            except json.JSONDecodeError:
                pass
        return [part.strip() for part in raw.split(",") if part.strip()]

    @property
    def field_map(self) -> list[FieldMapEntry]:
        try:
            data = json.loads(self.imanage_field_map_raw or "[]")
        except json.JSONDecodeError:
            data = []
        return [FieldMapEntry(e) for e in data]


@lru_cache
def get_settings() -> Settings:
    return Settings()
