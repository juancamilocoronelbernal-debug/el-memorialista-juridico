"""Streaming nativo, integridad y ausencia de falsos finales."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.services import despacho_stream as stream
from app.services.gemini_service import Motor, gemini_service
from app.routers import despacho_ai as router


@pytest.mark.asyncio
async def test_sse_reader_accepts_multiline_json_and_skips_heartbeat():
    async def lines():
        for line in [": heartbeat", 'data: {"candidates":', 'data: [{"content":{}}]}', "", "", "data: [DONE]", ""]:
            yield line
    assert [packet async for packet in stream.parse_provider_sse(lines())] == [
        {"candidates": [{"content": {}}]}
    ]


@pytest.mark.asyncio
async def test_gemini_stream_emits_real_deltas_and_terminal_metadata(monkeypatch):
    packets = [
        {"candidates": [{"content": {"parts": [{"text": "Hola "}, {"text": "secreto de pensamiento", "thought": True}]}}]},
        {"candidates": [{"content": {"parts": [{"text": "mundo"}]}, "finishReason": "STOP"}],
         "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 2}},
    ]
    sent = []
    def fake(request):
        sent.append(request)
        return httpx.Response(200, text="".join("data: " + json.dumps(p) + "\n\n" for p in packets),
                              headers={"Content-Type": "text/event-stream"})
    client = httpx.AsyncClient(transport=httpx.MockTransport(fake))
    monkeypatch.setattr(gemini_service, "candidatos", lambda _: [Motor("gemini", "gemini-3.6-flash")])
    monkeypatch.setattr(gemini_service, "_cliente", AsyncMock(return_value=client))
    monkeypatch.setattr(gemini_service, "_cab_gemini", lambda: {"x-goog-api-key": "test-only"})
    monkeypatch.setattr(stream, "get_settings", lambda: SimpleNamespace(GEMINI_API_BASE="https://gemini.local", GROQ_API_BASE="", GROQ_API_KEY="", GROQ_MAX_TOKENS=1000))
    try:
        events = [event async for event in stream.provider_events([("user", "saluda")], mode="general")]
    finally:
        await client.aclose()
    assert [event["data"]["text"] for event in events if event["event"] == "delta"] == ["Hola ", "mundo"]
    result = events[-1]["data"]
    assert events[-1]["event"] == "provider_done"
    assert result["answer"] == "Hola mundo"
    assert result["finish_reason"] == "STOP"
    assert result["usage"] == {"input_tokens": 100, "output_tokens": 2}
    assert "secreto de pensamiento" not in result["answer"]
    assert ":streamGenerateContent" in str(sent[0].url)
    assert "alt=sse" in str(sent[0].url)


@pytest.mark.asyncio
async def test_stream_fails_closed_if_provider_ends_after_partial_chunk(monkeypatch):
    packet = {"candidates": [{"content": {"parts": [{"text": "Cita posiblemente incompleta"}]}}]}
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(
        200, text="data: "+json.dumps(packet)+"\n\n", headers={"Content-Type": "text/event-stream"})))
    monkeypatch.setattr(gemini_service, "candidatos", lambda _: [Motor("gemini", "gemini-3.6-flash")])
    monkeypatch.setattr(gemini_service, "_cliente", AsyncMock(return_value=client))
    monkeypatch.setattr(gemini_service, "_cab_gemini", lambda: {})
    monkeypatch.setattr(stream, "get_settings", lambda: SimpleNamespace(GEMINI_API_BASE="https://gemini.local"))
    events = []
    try:
        with pytest.raises(HTTPException) as error:
            async for event in stream.provider_events([("user", "saluda")], mode="general"):
                events.append(event)
        assert error.value.status_code == 502
        assert [e["event"] for e in events].count("delta") == 1
        assert not any(e["event"] == "provider_done" for e in events)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_stream_chat_keeps_coverage_and_final_answer(monkeypatch):
    from app.services import despacho_ai as ai
    monkeypatch.setattr(ai, "load_context", AsyncMock(return_value=([], None, "", [])))
    async def augment(*args):
        return args[-1]
    monkeypatch.setattr(ai, "augment_indexed_context", augment)
    async def mock_provider(*args, **kwargs):
        yield {"event": "delta", "data": {"text": "Resultado "}}
        yield {"event": "delta", "data": {"text": "verificable"}}
        yield {"event": "provider_done", "data": {
            "answer": "Resultado verificable", "sources": [], "warnings": [], "provider": "gemini",
            "model": "prueba", "usage": {}, "search_performed": False}}
    monkeypatch.setattr(stream, "provider_events", mock_provider)
    events = [e async for e in stream.stream_chat("user", "token", {
        "message": "saluda", "history": [], "mode": "general", "knowledge_scope": "off", "document_ids": []})]
    assert [e["event"] for e in events] == ["status", "status", "delta", "delta", "done"]
    assert events[-1]["data"]["answer"] == "Resultado verificable"
    assert events[-1]["data"]["coverage"]["documents"] == 0
    assert events[-1]["data"]["plan"][-1]["status"] == "pending"


def test_sse_route_is_authenticated_rate_limited_and_not_buffered(monkeypatch):
    monkeypatch.setattr(router, "_identity", AsyncMock(return_value=("user", "token")))
    checks = []
    monkeypatch.setattr(router.limitador, "verificar", lambda *a, **kw: checks.append((a, kw)))
    async def mock_stream(*args):
        yield {"event": "delta", "data": {"text": "Hola"}}
        yield {"event": "done", "data": {"answer": "Hola"}}
    monkeypatch.setattr(router.despacho_stream, "stream_chat", mock_stream)
    app = FastAPI()
    app.include_router(router.router)
    with TestClient(app) as client:
        response = client.post("/api/despacho/chat/stream", json={"message": "hola"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert response.headers["x-accel-buffering"] == "no"
    assert "event: delta" in response.text and "event: done" in response.text
    assert checks and checks[0][0][1] == "redactar"
