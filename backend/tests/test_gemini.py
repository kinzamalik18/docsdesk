"""Gemini client tests against a mocked HTTP transport. No network calls."""

import json

import httpx
import pytest

from app.llm.gemini import GeminiError, GeminiProvider


def make_provider(handler) -> GeminiProvider:
    provider = GeminiProvider(api_key="test-key", chat_model="chat-m", embed_model="embed-m", dim=3)
    provider.client = httpx.Client(
        base_url="https://example.test",
        headers=provider.client.headers,
        transport=httpx.MockTransport(handler),
    )
    return provider


def test_embed_query_sends_task_type_and_normalizes(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["key"] = request.headers["x-goog-api-key"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"embedding": {"values": [3.0, 0.0, 4.0]}})

    vector = make_provider(handler).embed_query("hello")

    assert seen["path"].endswith("/models/embed-m:embedContent")
    assert seen["key"] == "test-key"
    assert seen["body"]["taskType"] == "RETRIEVAL_QUERY"
    assert seen["body"]["outputDimensionality"] == 3
    assert vector == pytest.approx([0.6, 0.0, 0.8])


def test_generate_json_returns_text_parts():
    def handler(request):
        body = json.loads(request.content)
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]})

    assert make_provider(handler).generate_json("sys", "prompt") == '{"ok": true}'


def test_retries_on_rate_limit(monkeypatch):
    monkeypatch.setattr("app.llm.gemini.time.sleep", lambda s: None)
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, headers={"retry-after": "1"}, json={})
        return httpx.Response(200, json={"embedding": {"values": [1.0, 0.0, 0.0]}})

    make_provider(handler).embed_query("hi")
    assert calls["n"] == 3


def test_blocked_response_raises_clear_error():
    def handler(request):
        return httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})

    with pytest.raises(GeminiError, match="no content"):
        make_provider(handler).generate_json("s", "p")


def test_client_error_is_not_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(400, json={"error": "bad key"})

    with pytest.raises(GeminiError, match="400"):
        make_provider(handler).embed_query("x")
    assert calls["n"] == 1
