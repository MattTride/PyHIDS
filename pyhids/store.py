"""
pyhids.store — SQLite 事件持久化层
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

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

