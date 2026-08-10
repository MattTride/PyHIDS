import asyncio
from datetime import datetime

from fastapi.testclient import TestClient

from pyhids import web
from pyhids.store import Event

client = TestClient(web.app)

def test_api_events_returns_json(monkeypatch):
    fake_events = [
        Event(
            detected_at=datetime(2026, 5, 21, 20, 30, 0),
            source="ssh_brute_force",
            severity="critical",
            summary="1.2.3.4 暴力破解嫌疑",
            payload={"ip" : "1.2.3.4"},
        )
    ]
    monkeypatch.setattr(web, "query_events", lambda **kwargs: fake_events)

    response = client.get("/api/events")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["severity"] == "critical"
    assert data[0]["source"] == "ssh_brute_force"
    assert data[0]["detected_at"] == "2026-05-21T20:30:00"
    assert data[0]["summary"] == "1.2.3.4 暴力破解嫌疑"

def test_dashboard_page_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "PyHIDS" in response.text
    assert "row.innerHTML" not in response.text
    assert "cell.textContent" in response.text

def test_api_events_forwards_filters(monkeypatch):
    captured = {}
    def fake_query(**kwargs):
        captured.update(kwargs)
        return []
    monkeypatch.setattr(web, "query_events", fake_query)

    client.get("/api/events?source=ssh_brute_force&severity=critical")

    assert captured["source"] == "ssh_brute_force"
    assert captured["severity"] == "critical"
def test_api_events_forwards_pagination(monkeypatch):
    captured = {}
    def fake_query(**kwargs):
        captured.update(kwargs)
        return []
    monkeypatch.setattr(web, "query_events", fake_query)

    client.get("/api/events?limit=20&offset=40")

    assert captured["limit"] == 20
    assert captured["offset"] == 40


def test_api_events_rejects_invalid_pagination():
    assert client.get("/api/events?limit=0").status_code == 422
    assert client.get("/api/events?limit=101").status_code == 422
    assert client.get("/api/events?offset=-1").status_code == 422

def test_cursor_stream_pushes_the_current_cursor_first(monkeypatch):
    """SSE 连上后应立刻推一次当前游标，前端不用等到第一条新事件才知道状态。

    直接测生成器，不走 TestClient —— 它是无限流，用 HTTP 连接去测会永远等不到结束。
    """
    monkeypatch.setattr(web, "max_event_id", lambda: 42)

    async def first_message():
        gen = web.cursor_stream()
        try:
            return await anext(gen)
        finally:
            await gen.aclose()

    assert asyncio.run(first_message()) == 'data: {"max_id": 42}\n\n'

def test_cursor_stream_emits_a_new_message_only_when_the_cursor_moves(monkeypatch):
    """id 没变就发 keep-alive 注释行，变了才发 data。"""
    ids = iter([7, 7, 9])
    monkeypatch.setattr(web, "max_event_id", lambda: next(ids))
    monkeypatch.setattr(web, "STREAM_POLL_SECONDS", 0)

    async def three_messages():
        gen = web.cursor_stream()
        try:
            return [await anext(gen), await anext(gen), await anext(gen)]
        finally:
            await gen.aclose()

    first, second, third = asyncio.run(three_messages())
    assert first == 'data: {"max_id": 7}\n\n'
    assert second == ": keep-alive\n\n"
    assert third == 'data: {"max_id": 9}\n\n'

def test_stream_route_is_registered():
    assert "/api/stream" in {route.path for route in web.app.routes}
