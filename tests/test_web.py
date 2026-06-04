from datetime import datetime
from fastapi.testclient import TestClient
from pyhids.store import Event
from pyhids import web

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