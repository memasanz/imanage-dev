"""iManage AI Workspace — backend proxy.

Fronts APIM routes, normalizes iManage responses to neutral shapes, manages per-session auth,
and bridges agent turns to the Foundry hosted agent. Serves the built SPA under /ui.
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .imanage_client import UpstreamError
from .routers import agent, auth, browse, documents, meta, search

app = FastAPI(title="iManage AI Workspace — Proxy", version="0.1.0")

# Dev CORS: the Vite dev server runs on a different port. In production the SPA is same-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(search.router, prefix="/api")
app.include_router(browse.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(agent.router, prefix="/api")


@app.exception_handler(UpstreamError)
async def upstream_error_handler(request: Request, exc: UpstreamError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status if exc.status >= 400 else 502,
        content={"error": {"code": "upstream_error", "message": exc.message, "correlation_id": ""}},
    )


# Serve the built SPA under /ui (present in the container image; absent during local backend dev).
_ui_dir = os.path.join(os.path.dirname(__file__), "..", "ui")
if os.path.isdir(_ui_dir):
    app.mount("/ui", StaticFiles(directory=_ui_dir, html=True), name="ui")


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui/")
