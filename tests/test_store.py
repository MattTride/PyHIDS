import sqlite3

from datetime import datetime
from pyhids.store import init_db
from pyhids.store import Event, insert_event, query_events
from pyhids.store import dedup_key
from pyhids.store import dedup_keys_since

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

def test_dedup_key_ssh_uses_ip():
    ev = Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="ssh_brute_force",
        severity="critical",
        summary="1.2.3.4 暴破嫌疑 (5次 / 窗口)",
        payload={"ip": "1.2.3.4", "fail_count": 5},
    )
    assert dedup_key(ev) == "ssh_brute_force:1.2.3.4"

def test_dedup_key_file_users_source_and_summary():
    ev = Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="file_integrity",
        severity="critical",
        summary="/etc/passwd modified",
        payload={"file_path": "/etc/passwd", "change":"modified"}
    )
    assert dedup_key(ev) == "file_integrity:/etc/passwd modified"

def test_dedup_key_ssh_stable_despite_changing_window():
    ev1 = Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="ssh_brute_force",
        severity="critical",
        summary="1.2.3.4 暴破嫌疑 (3次 / 窗口)",
        payload={"ip": "1.2.3.4", "fail_count": 5},
    )
    assert dedup_key(ev1) == "ssh_brute_force:1.2.3.4"

    ev2 = Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="ssh_brute_force",
        severity="critical",
        summary="1.2.3.4 暴力破解 (6次 / 窗口)",
        payload={"ip": "1.2.3.4", "fail_count": 6},
    )
    assert dedup_key(ev2) == "ssh_brute_force:1.2.3.4"
    assert dedup_key(ev1) == dedup_key(ev2)

def test_dedup_keys_since_filter_by_time(tmp_path):
    db_path = tmp_path / "events.db"
    init_db(db_path)

    old = Event(
        detected_at=datetime(2026, 1, 1, 0, 0, 0),
        source="ssh_brute_force", severity="critical",
        summary="old attack", payload={"ip": "9.9.9.9"},
    )
    new = Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="ssh_brute_force", severity="critical",
        summary="new attack", payload={"ip": "1.2.3.4"},
    )
    insert_event(old, db_path)
    insert_event(new, db_path)

    # 截止时间卡在 old(1月) 和 new(5月) 之间
    keys = dedup_keys_since(datetime(2026, 5, 1, 0, 0, 0), db_path=db_path)

    assert keys == {"ssh_brute_force:1.2.3.4"}   # 只剩 new，old 在窗口外被排除


def test_dedup_keys_since_empty_when_nothing_recent(tmp_path):
    db_path = tmp_path / "events.db"
    init_db(db_path)

    old = Event(
        detected_at=datetime(2026, 1, 1, 0, 0, 0),
        source="ssh_brute_force", severity="critical",
        summary="old attack", payload={"ip": "9.9.9.9"},
    )
    insert_event(old, db_path)


    keys = dedup_keys_since(datetime(2026, 6, 1, 0, 0, 0), db_path=db_path)

    assert keys == set()


def test_query_events_filters_by_severity(tmp_path):
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

    events = query_events(severity="critical", db_path=db_path)

    assert len(events) == 1
    assert events[0].severity == "critical"