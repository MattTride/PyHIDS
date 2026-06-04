"""
pyhids.web - 事件仪表盘的Web应用
"""
from __future__ import annotations
from fastapi import FastAPI
from pyhids.store import query_events

app = FastAPI(title="PyHIDS Dashboard")

@app.get("/api/events")
def api_events(limit: int = 50, source: str | None =None) -> list[dict]:
    """返回最近的事件，最新在前"""
    events = query_events(limit=limit, source=source)
    return [
        {
            "detected_at": e.detected_at.isoformat(),
            "source": e.source,
            "severity": e.severity,
            "summary": e.summary,
            "payload": e.payload,
        }
        for e in events
    ]