"""
pyhids.store — SQLite 事件持久化层
"""
from __future__ import annotations

import json
import logging
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

DEFAULT_DB_PATH = Path("data/events.db")

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

def query_events(
        limit: int = 50,
        source: str | None = None,
        db_path: Path = DEFAULT_DB_PATH,
) -> list[Event]:
    """
    查询最近的事件，按时间倒序。

    Args:
        limit: 最多返回多少条
        source: 可选，按 source 字段过滤（None 表示不过滤）

    Returns:
        Event 列表，最新的在前
    """
    conn = sqlite3.connect(db_path)

    if source is not None:
        SQL = """
            SELECT detected_at, source, severity, summary, payload
            FROM events
            WHERE source = ?
            ORDER BY detected_at DESC
            LIMIT ?
        """
        params = (source, limit)
    else:
        SQL = """
            SELECT detected_at, source, severity, summary, payload
            FROM events
            ORDER BY detected_at DESC
            LIMIT ?
        """
        params = (limit,)

    cursor = conn.execute(SQL, params)
    rows = cursor.fetchall()
    conn.close()

    events = []
    for row in rows:
        events.append(Event(detected_at=datetime.fromisoformat(row[0]),source=row[1],severity=row[2],summary=row[3],payload=json.loads(row[4])))

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


