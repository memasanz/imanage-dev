"""Per-browser-session state: iManage Work + MCP tokens and the agent document context.

Tokens are held in memory only, keyed by an opaque session id stored in a signed cookie.
They are never shared across sessions, never logged, and never returned to the client.
"""
from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field


@dataclass
class Session:
    work_token: str | None = None
    mcp_token: str | None = None
    work_refresh: str | None = None
    mcp_refresh: str | None = None
    context_docs: dict[str, str] = field(default_factory=dict)  # id -> name


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def new_id(self) -> str:
        return secrets.token_urlsafe(32)

    def get(self, sid: str | None) -> Session | None:
        if not sid:
            return None
        with self._lock:
            return self._sessions.get(sid)

    def get_or_create(self, sid: str | None) -> tuple[str, Session]:
        with self._lock:
            if sid and sid in self._sessions:
                return sid, self._sessions[sid]
            new = self.new_id()
            self._sessions[new] = Session()
            return new, self._sessions[new]

    def clear(self, sid: str | None) -> None:
        if not sid:
            return
        with self._lock:
            self._sessions.pop(sid, None)


store = SessionStore()
