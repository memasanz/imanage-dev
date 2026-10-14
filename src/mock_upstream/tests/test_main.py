from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"X-Auth-Token": "mock-token"}


def test_libraries_list():
    response = client.get("/work/api/v2/customers/mock-customer/libraries", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 3
    assert {library["id"] for library in body["data"]} == {"ACTIVE_US", "ARCHIVE_US", "EU_WORK"}


def test_documents_search_returns_custom_fields_and_descriptions():
    response = client.post(
        "/work/api/v2/customers/mock-customer/documents/search?libraries=ACTIVE_US&exclude_emails=true",
        headers=HEADERS,
        json={"title": "Falcon", "filters": {"custom1": "412117"}, "page_size": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] >= 1
    doc = body["data"][0]
    assert doc["custom1"] == "412117"
    assert doc["custom1_description"] == "Acme Corporation"
    assert doc["custom2"] == "0001"
    assert doc["custom2_description"] == "Project Falcon Acquisition"
    assert doc["author"]
    assert doc["author_description"]
    assert doc["class"]
    assert doc["class_description"]
    assert not doc["is_email"]


def test_document_text_fetch():
    response = client.get("/work/api/v2/customers/mock-customer/documents/ACTIVE_US!1001.3/text", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "ACTIVE_US!1001.3"
    assert "Merger Agreement" in body["text"]
    assert body["source"] == "work"


def test_mcp_tools_call_fetch():
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "fetch", "arguments": {"id": "ACTIVE_US!1001.3"}}},
        headers={"Authorization": "Bearer mock"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["jsonrpc"] == "2.0"
    assert body["id"] == 1
    assert body["result"]["isError"] is False
    assert "indemnification" in body["result"]["content"][0]["text"]
