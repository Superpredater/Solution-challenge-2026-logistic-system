"""Edge Agent — LocalBuffer: SQLite-backed event buffer for offline operation."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


class LocalBuffer:
    """SQLite-backed buffer for shipment events during offline periods (Req 19.1)."""

    def __init__(self, db_path: str = "edge_buffer.db") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS event_buffer (
                id INTEGER PRIMARY KEY,
                event_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                synced INTEGER DEFAULT 0
            )
            """
        )
        self._conn.commit()

    def add_event(self, event: dict[str, Any], recorded_at: str) -> None:
        """Insert an event into the buffer."""
        self._conn.execute(
            "INSERT INTO event_buffer (event_json, recorded_at, synced) VALUES (?, ?, 0)",
            (json.dumps(event), recorded_at),
        )
        self._conn.commit()

    def get_unsynced_events(self, limit: int = 500) -> list[dict[str, Any]]:
        """Return up to `limit` unsynced events ordered by recorded_at ASC."""
        cursor = self._conn.execute(
            "SELECT id, event_json, recorded_at FROM event_buffer "
            "WHERE synced = 0 ORDER BY recorded_at ASC LIMIT ?",
            (limit,),
        )
        return [
            {
                "id": row[0],
                "event": json.loads(row[1]),
                "recorded_at": row[2],
            }
            for row in cursor.fetchall()
        ]

    def mark_synced(self, ids: list[int]) -> None:
        """Mark the given event IDs as synced."""
        if not ids:
            return
        placeholders = ",".join("?" * len(ids))
        self._conn.execute(
            f"UPDATE event_buffer SET synced = 1 WHERE id IN ({placeholders})",
            ids,
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
