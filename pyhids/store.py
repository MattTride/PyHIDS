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
    # "ssh_rute_force"
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

    logger.info("写入事件id=%s sourse=%s", new_id, event.source)
    return new_id

