"""SQLite index over the session/photo files on disk.

The files on disk are the source of truth; this database is a fast,
rebuildable index that powers the idle-screen slideshow and future gallery
browsing. It stores paths and metadata only -- never image bytes.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from contextlib import closing
from datetime import datetime
from pathlib import Path

from photobooth.core.session import CaptureSession

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    filter_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    path TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('shot', 'result')),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_photos_kind_created ON photos(kind, created_at DESC);
"""


class PhotoDatabase:
    def __init__(self, db_path: Path) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def record_session(self, session: CaptureSession) -> None:
        with closing(self._conn.cursor()) as cur:
            cur.execute(
                "INSERT OR REPLACE INTO sessions (id, mode, filter_name, created_at) "
                "VALUES (?, ?, ?, ?)",
                (session.id, session.mode, session.filter_name, session.created_at.isoformat()),
            )
        self._conn.commit()

    def record_photo(self, session_id: str, path: Path, kind: str) -> None:
        with closing(self._conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO photos (session_id, path, kind, created_at) VALUES (?, ?, ?, ?)",
                (session_id, str(path), kind, datetime.now().isoformat()),
            )
        self._conn.commit()

    def recent_results(self, limit: int = 30) -> list[Path]:
        with closing(self._conn.cursor()) as cur:
            cur.execute(
                "SELECT path FROM photos WHERE kind = 'result' "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows: Iterable[tuple[str]] = cur.fetchall()
        return [Path(row[0]) for row in rows if Path(row[0]).is_file()]

    def all_results(self) -> list[Path]:
        """Every result photo on record, newest first -- backs the Gallery
        screen (unlike recent_results, which is capped for the idle-screen
        slideshow)."""
        with closing(self._conn.cursor()) as cur:
            cur.execute("SELECT path FROM photos WHERE kind = 'result' ORDER BY created_at DESC")
            rows: Iterable[tuple[str]] = cur.fetchall()
        return [Path(row[0]) for row in rows if Path(row[0]).is_file()]
