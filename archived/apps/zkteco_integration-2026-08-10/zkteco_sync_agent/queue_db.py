# Copyright (c) 2026, Exacuer
"""Local SQLite offline queue for unsynced attendance."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS attendance_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name TEXT NOT NULL,
    zkteco_user_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    log_type TEXT,
    payload TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(device_name, zkteco_user_id, timestamp)
);

CREATE TABLE IF NOT EXISTS sync_state (
    device_name TEXT PRIMARY KEY,
    last_att_stamp TEXT,
    updated_at TEXT
);
"""


class AttendanceQueue:
	def __init__(self, db_path: str | Path):
		self.db_path = Path(db_path)
		self.db_path.parent.mkdir(parents=True, exist_ok=True)
		self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
		self._conn.row_factory = sqlite3.Row
		self._conn.executescript(SCHEMA)
		self._conn.commit()

	def enqueue(self, device_name: str, zkteco_user_id: str, timestamp: str, log_type: str | None, payload: dict | None = None) -> bool:
		"""Insert if not duplicate. Returns True if inserted."""
		try:
			self._conn.execute(
				"""
				INSERT INTO attendance_queue
				(device_name, zkteco_user_id, timestamp, log_type, payload, status, created_at)
				VALUES (?, ?, ?, ?, ?, 'pending', ?)
				""",
				(
					device_name,
					str(zkteco_user_id),
					timestamp,
					log_type,
					json.dumps(payload or {}),
					datetime.now().isoformat(sep=" ", timespec="seconds"),
				),
			)
			self._conn.commit()
			return True
		except sqlite3.IntegrityError:
			return False

	def pending(self, limit: int = 200) -> list[dict[str, Any]]:
		cur = self._conn.execute(
			"""
			SELECT * FROM attendance_queue
			WHERE status IN ('pending', 'failed')
			ORDER BY timestamp ASC
			LIMIT ?
			""",
			(limit,),
		)
		return [dict(r) for r in cur.fetchall()]

	def mark_synced(self, row_id: int) -> None:
		self._conn.execute(
			"UPDATE attendance_queue SET status='synced', last_error=NULL WHERE id=?",
			(row_id,),
		)
		self._conn.commit()

	def mark_failed(self, row_id: int, error: str) -> None:
		self._conn.execute(
			"""
			UPDATE attendance_queue
			SET status='failed', retry_count=retry_count+1, last_error=?
			WHERE id=?
			""",
			(error[:500], row_id),
		)
		self._conn.commit()

	def get_last_att_stamp(self, device_name: str) -> str | None:
		cur = self._conn.execute(
			"SELECT last_att_stamp FROM sync_state WHERE device_name=?",
			(device_name,),
		)
		row = cur.fetchone()
		return row["last_att_stamp"] if row else None

	def set_last_att_stamp(self, device_name: str, stamp: str) -> None:
		self._conn.execute(
			"""
			INSERT INTO sync_state(device_name, last_att_stamp, updated_at)
			VALUES (?, ?, ?)
			ON CONFLICT(device_name) DO UPDATE SET
				last_att_stamp=excluded.last_att_stamp,
				updated_at=excluded.updated_at
			""",
			(device_name, stamp, datetime.now().isoformat(sep=" ", timespec="seconds")),
		)
		self._conn.commit()

	def close(self) -> None:
		self._conn.close()
