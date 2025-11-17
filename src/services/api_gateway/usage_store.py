import os
import sqlite3
import time
import hashlib
from typing import Optional, Dict, Any, List, Tuple

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.getenv("USAGE_DB_PATH", os.path.join(BASE_DIR, "usage.sqlite3"))


def _conn():
    cx = sqlite3.connect(DB_PATH)
    cx.execute("PRAGMA journal_mode=WAL;")
    cx.execute("PRAGMA synchronous=NORMAL;")
    return cx


def init_db() -> None:
    with _conn() as cx:
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts INTEGER NOT NULL,
              minute_window INTEGER NOT NULL,
              api_key TEXT NOT NULL,
              plan TEXT NOT NULL,
              endpoint TEXT NOT NULL,
              count INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        cx.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_usage_minute_key ON usage_events(minute_window, api_key)
            """
        )


def record_usage(api_key: str, plan: str, endpoint: str) -> None:
    now = int(time.time())
    window = now // 60
    key_hash = hashlib.sha256((api_key or "").encode("utf-8")).hexdigest()
    with _conn() as cx:
        # Upsert by (minute_window, api_key, endpoint)
        row = cx.execute(
            "SELECT id, count FROM usage_events WHERE minute_window=? AND api_key=? AND endpoint=?",
            (window, key_hash, endpoint),
        ).fetchone()
        if row:
            cx.execute("UPDATE usage_events SET count=? WHERE id=?", (row[1] + 1, row[0]))
        else:
            cx.execute(
                "INSERT INTO usage_events (ts, minute_window, api_key, plan, endpoint, count) VALUES (?, ?, ?, ?, ?, 1)",
                (now, window, key_hash, plan, endpoint),
            )


def summarize(date_epoch_day: Optional[int] = None) -> List[Dict[str, Any]]:
    # date_epoch_day: days since epoch, if None, use today
    if date_epoch_day is None:
        date_epoch_day = int(time.time()) // 86400
    start = date_epoch_day * 86400
    end = start + 86400
    start_window = start // 60
    end_window = end // 60
    with _conn() as cx:
        rows = cx.execute(
            """
            SELECT api_key, plan, endpoint, SUM(count) as total
            FROM usage_events
            WHERE minute_window >= ? AND minute_window < ?
            GROUP BY api_key, plan, endpoint
            ORDER BY total DESC
            """,
            (start_window, end_window),
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({"api_key": r[0], "plan": r[1], "endpoint": r[2], "total": r[3]})
    return out
