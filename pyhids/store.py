"""
pyhids.store — SQLite 事件持久化层
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime



@dataclass
class Event:
    """一条等待写入数据库的事件(内存表示)"""
    detected_at: datetime
    source: str
    # "ssh_brute_force"
    severity: str
    summary: str
    payload: dict

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(os.getenv("PYHIDS_DB_PATH", "data/events.db"))

# language=SQL
SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at TEXT NOT NULL,
    source TEXT NOT NULL,
    severity TEXT NOT NULL,
    summary TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_detected_at ON events(detected_at);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
"""

def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """
    初始化 events 表和索引。幂等：可以重复调用。
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))

    conn.executescript(SCHEMA)

    conn.commit()
    conn.close()

    logger.info("已初始化数据库 %s", db_path)

def insert_event(event: Event, db_path: Path = DEFAULT_DB_PATH) -> int:
    conn = sqlite3.connect(str(db_path))

    SQL = """
          INSERT INTO events (detected_at, source, severity, summary, payload)
          VALUES (?, ?, ?, ?, ?) \
          """

    params = (event.detected_at.isoformat(), event.source, event.severity, event.summary, json.dumps(event.payload, ensure_ascii=False))

    cursor = conn.execute(SQL, params)

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    logger.info("写入事件id=%s source=%s", new_id, event.source)
    return new_id

def max_event_id(db_path: Path = DEFAULT_DB_PATH) -> int:
    """当前最大事件 id，空库返回 0。SSE 用它当"有没有新事件"的游标。"""
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT MAX(id) FROM events").fetchone()
    conn.close()
    # 空表时 MAX() 返回 NULL → Python 的 None
    return row[0] if row[0] is not None else 0


def query_events(
        limit: int = 50,
        offset: int = 0,
        source: str | None = None,
        severity: str | None = None,
        db_path: Path = DEFAULT_DB_PATH,
) -> list[Event]:
    """查询最近的事件，按时间倒序。source / severity 可选过滤（None=不过滤）。

    offset 用于分页：跳过前 offset 条。
    """
    conn = sqlite3.connect(db_path)

    clauses = []
    params = []
    if source is not None:
        clauses.append("source = ?")
        params.append(source)
    if severity is not None:
        clauses.append("severity = ?")
        params.append(severity)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    SQL = f"""
        SELECT detected_at, source, severity, summary, payload
        FROM events
        {where}
        ORDER BY detected_at DESC
        LIMIT ? OFFSET ?
    """
    params.append(limit)
    params.append(offset)

    cursor = conn.execute(SQL, params)
    rows = cursor.fetchall()
    conn.close()

    events = []
    for row in rows:
        events.append(Event(
            detected_at=datetime.fromisoformat(row[0]),
            source=row[1], severity=row[2], summary=row[3],
            payload=json.loads(row[4]),
        ))
    return events


def print_events_table(events: list[Event]) -> None:
    """以表格形式把事件列表打印到 stdout。"""
    if not events:
        print("（没有事件）")
        return

    # 表头
    print(f"\n{'TIME':<20} {'SOURCE':<18} {'SEVERITY':<10} SUMMARY")
    print("-" * 80)

    # 每行一条事件
    for ev in events:
        time_str = ev.detected_at.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{time_str:<20} {ev.source:<18} {ev.severity:<10} {ev.summary}")

    print(f"\n共 {len(events)} 条事件")

def dedup_key(event: Event) -> str:
    """事件的稳定指纹，用来去重"""
    if event.source == "ssh_brute_force":
        return f"ssh_brute_force:{event.payload['ip']}"
    if event.source == "privilege_escalation":
        # 按"谁 + 哪类滥用"去重，不带窗口时间 —— 否则窗口一挪指纹就变，去重失效
        return f"privilege_escalation:{event.payload['user']}:{event.payload['kind']}"
    return f"{event.source}:{event.summary}"

def dedup_keys_since(since: datetime, db_path: Path = DEFAULT_DB_PATH) -> set[str]:
    """返回detected_at >= since的所有事件去重指纹集合"""
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT detected_at, source, severity, summary, payload FROM events WHERE detected_at >= ?",
        (since.isoformat(),),
    ).fetchall()
    conn.close()

    events = [
        Event(
            detected_at=datetime.fromisoformat(r[0]),
            source=r[1],
            severity=r[2],
            summary=r[3],
            payload=json.loads(r[4]),
        )
        for r in rows
    ]
    return {dedup_key(e) for e in events}