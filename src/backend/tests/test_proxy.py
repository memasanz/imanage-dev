"""Smoke tests for the proxy — mock mode, normalization, and config endpoints.

These run without network by exercising normalization directly and the FastAPI app via
TestClient for the endpoints that don't require the mock upstream.
"""
from __future__ import annotations

import os

os.environ.setdefault("IMANAGE_BACKEND_MODE", "mock")
os.environ.setdefault(
    "IMANAGE_FIELD_MAP",
    '[{"key":"client","source":"custom1","label":"Client","searchable":true,"filterable":true,"show_in_detail":true}]',
)

from fastapi.testclient import TestClient  # noqa: E402

from app.config import FieldMapEntry  # noqa: E402
from app.main import app  # noqa: E402
from app.normalize import filters_to_imanage, normalize_document  # noqa: E402

client = TestClient(app)


def test_health_mock_mode():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "mock"
    assert body["work_connected"] is False


def test_config_exposes_mapped_fields():
    r = client.get("/api/config")
    assert r.status_code == 200
    keys = [f["key"] for f in r.json()["fields"]]
    assert "client" in keys


def test_normalize_resolves_code_description_pair():
    field_map = [FieldMapEntry({"key": "client", "source": "custom1", "label": "Client"})]
    raw = {
        "id": "ACTIVE_US!1.1",
        "name": "Merger",
        "custom1": "412117",
        "custom1_description": "Acme Corp",
        "author": "jsmith",
        "author_description": "Jane Smith",
    }
    doc = normalize_document(raw, field_map)
    assert doc["fields"]["client"] == {"id": "412117", "text": "Acme Corp"}
    assert doc["author"] == {"id": "jsmith", "text": "Jane Smith"}


def test_filters_translate_back_to_customn():
    field_map = [FieldMapEntry({"key": "client", "source": "custom1", "label": "Client"})]
    out = filters_to_imanage([{"key": "client", "op": "is", "value": "412117"}], field_map)
    assert out == {"custom1": "412117"}


class _Item:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    """Minimal stand-in for an OpenAI Responses payload."""

    def __init__(self, output):
        self.output = output

    def model_dump_json(self):
        import json

        return json.dumps({"output": [i.__dict__ for i in self.output]})


def test_consent_detected_from_oauth_consent_request_item():
    from app.agent_bridge import _consent_url_from_response

    resp = _Resp([
        _Item(
            type="oauth_consent_request",
            consent_link="https://logic-apis-eastus2.consent.azure-apim.net/login?data=abc",
            server_label="imanage",
        )
    ])
    assert _consent_url_from_response(resp) == (
        "https://logic-apis-eastus2.consent.azure-apim.net/login?data=abc"
    )


def test_consent_detected_from_legacy_jsonrpc_marker():
    from app.agent_bridge import _consent_url_from_response

    resp = _Resp([
        _Item(
            type="mcp_call",
            error="-32006 CONSENT_REQUIRED: visit https://example.consent.test/authorize to connect",
        )
    ])
    assert _consent_url_from_response(resp) == "https://example.consent.test/authorize"


def test_no_consent_for_normal_response():
    from app.agent_bridge import _consent_url_from_response

    resp = _Resp([_Item(type="message", content="Here is the answer.")])
    assert _consent_url_from_response(resp) is None
