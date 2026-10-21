import time

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("ADMIN_TOKEN", "secret-token")
    monkeypatch.setenv("MIN_SIMILARITY", "0.2")
    monkeypatch.setenv("EVAL_DELAY_SECONDS", "0")
    monkeypatch.setenv("CHAT_RATE_LIMIT", "3")
    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


ADMIN = {"X-Admin-Token": "secret-token"}


def test_startup_indexes_sample_docs(client):
    info = client.get("/api/info").json()
    assert info["company"] == "Fernbill"
    assert info["provider"] == "fake"
    assert info["chunks"] > 30
    assert len(client.get("/api/sources").json()) == 14


def test_chat_returns_cited_answer(client):
    response = client.post("/api/chat", json={"question": "How do I set up two-factor authentication?"})
    body = response.json()
    assert response.status_code == 200
    assert body["answered"] is True
    assert body["citations"][0]["snippet"]


def test_chat_validates_input(client):
    assert client.post("/api/chat", json={"question": ""}).status_code == 422
    assert client.post("/api/chat", json={"question": "x" * 1001}).status_code == 422


def test_chat_rate_limit(client):
    codes = [client.post("/api/chat", json={"question": "pricing"}).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_gaps_need_admin_token_by_default(client):
    assert client.get("/api/gaps").status_code == 401
    assert client.get("/api/gaps", headers=ADMIN).status_code == 200


def test_admin_endpoints_reject_wrong_token(client):
    assert client.post("/api/admin/reindex", headers={"X-Admin-Token": "nope"}).status_code == 401
    assert client.post("/api/admin/eval").status_code == 401


def test_upload_and_delete_document(client):
    files = {"file": ("shipping-policy.md", b"# Shipping policy\n\nWe ship worldwide within 5 days.", "text/markdown")}
    uploaded = client.post("/api/admin/documents", files=files, headers=ADMIN)
    assert uploaded.status_code == 200
    assert uploaded.json()["doc_id"] == "shipping-policy"

    assert client.delete("/api/admin/documents/shipping-policy", headers=ADMIN).status_code == 204
    assert client.delete("/api/admin/documents/shipping-policy", headers=ADMIN).status_code == 404


def test_upload_rejects_unsupported_file(client):
    files = {"file": ("photo.png", b"\x89PNG", "image/png")}
    assert client.post("/api/admin/documents", files=files, headers=ADMIN).status_code == 400


def test_eval_runs_in_background(client):
    assert client.post("/api/admin/eval", headers=ADMIN).status_code == 202
    for _ in range(50):
        state = client.get("/api/eval/latest").json()
        if state["status"]["state"] == "done":
            break
        time.sleep(0.1)
    assert state["report"]["summary"]["total"] == 32


def test_feedback_accepted(client):
    response = client.post("/api/feedback", json={"question": "q", "answer": "a", "helpful": True})
    assert response.status_code == 204
