import sqlite3

from datetime import datetime
from pyhids.store import init_db
from pyhids.store import Event, insert_event, query_events

def test_init_db_creates_database_file_and_is_idempotent(tmp_path):
    db_path = tmp_path / "nested" / "events.db"

    init_db(db_path)
    init_db(db_path)

    assert db_path.is_file()

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'events'"
        ).fetchone()
    finally:
        conn.close()

    assert row == ("events",)

def test_insert_event_returns_id_and_preserves_chinese_payload(tmp_path):
    db_path = tmp_path / "events.db"
    init_db(db_path)

    event = Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="ssh_brute_force",
        severity="critical",
        summary="检测到中文事件",
        payload={"ip": "1.2.3.4", "message": "中文 payload"},
    )
    event_id = insert_event(event, db_path)

    assert event_id == 1
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT summary, payload FROM events WHERE id = ?",
            (event_id,),
        ).fetchone()
    finally:
        conn.close()

    assert row[0] == "检测到中文事件"
    assert "中文 payload" in row[1]
    assert "\\u4e2d" not in row[1]

def test_query_events_returns_newest_first(tmp_path):
    db_path = tmp_path / "events.db"
    init_db(db_path)

    insert_event(Event(
        detected_at=datetime(2026, 3, 1, 12, 0, 0),
        source="file_integrity",
        severity="warning",
        summary="middle",
        payload={},
    ), db_path)
    insert_event(Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="file_integrity",
        severity="warning",
        summary="newest",
        payload={},
    ), db_path)
    insert_event(Event(
        detected_at=datetime(2026, 1, 1, 12, 0, 0),
        source="file_integrity",
        severity="warning",
        summary="oldest",
        payload={},
    ), db_path)

    events = query_events(db_path=db_path)
    summaries = [e.summary for e in events]
    assert summaries == ["newest", "middle", "oldest"]

def test_query_events_filters_by_source(tmp_path):
    db_path = tmp_path / "events.db"
    init_db(db_path)

    insert_event(Event(
        detected_at=datetime(2026, 1, 1, 12, 0, 0),
        source="file_integrity",
        severity="warning",
        summary="fim event",
        payload={},
    ), db_path)
    insert_event(Event(
        detected_at=datetime(2026, 1, 2, 12, 0, 0),
        source="ssh_brute_force",
        severity="critical",
        summary="ssh event",
        payload={},
    ), db_path)

    events = query_events(source="ssh_brute_force", db_path=db_path)

    assert len(events) == 1
    assert events[0].source == "ssh_brute_force"
    assert events[0].summary == "ssh event"

def test_query_events_deserializes_types(tmp_path):
    db_path = tmp_path / "events.db"
    init_db(db_path)

    insert_event(Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="ssh_brute_force",
        severity="critical",
        summary="round trip",
        payload={"ip": "1.2.3.4", "count": 5},
    ), db_path)

    events = query_events(db_path=db_path)
    event = events[0]

    assert isinstance(event.detected_at,datetime)
    assert event.detected_at == datetime(2026, 5, 21, 20, 30, 0)
    assert isinstance(event.payload, dict)
    assert event.payload == {"ip": "1.2.3.4", "count": 5}
