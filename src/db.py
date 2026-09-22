from __future__ import annotations
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

PLAYLIST_SCHEMA = """
CREATE TABLE IF NOT EXISTS playlist_entries (
 serial_number INTEGER PRIMARY KEY,
 spotify_playlist_id TEXT NOT NULL,
 spotify_playlist_entry_number INTEGER NOT NULL,
 spotify_id TEXT NOT NULL,
 title TEXT NOT NULL,
 artist TEXT NOT NULL,
 album TEXT,
 isrc TEXT,
 status TEXT DEFAULT 'pending',
 error_remark TEXT DEFAULT NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(spotify_playlist_id, spotify_playlist_entry_number)
);
"""
SONGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS songs (
 serial_number INTEGER PRIMARY KEY,
 spotify_id TEXT UNIQUE NOT NULL,
 title TEXT NOT NULL,
 artist TEXT NOT NULL,
 album TEXT,
 album_artist TEXT,
 release_date TEXT,
 duration INTEGER,
 spotify_url TEXT,
 isrc TEXT,
 artwork_url TEXT,
 youtube_url TEXT,
 youtube_offset_seconds REAL,
 file_path TEXT,
 lrc_path TEXT,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_dbs(root: Path):
    p = connect(root / "playlist.db"); p.executescript(PLAYLIST_SCHEMA); p.commit(); p.close()
    s = connect(root / "songs.db"); s.executescript(SONGS_SCHEMA); s.commit(); s.close()

def utc_now(): return datetime.now(timezone.utc).isoformat()

def next_serial(c):
    return int(c.execute("SELECT COALESCE(MAX(serial_number),0)+1 FROM playlist_entries").fetchone()[0])

def set_status(c, serial, status, error=None):
    c.execute("UPDATE playlist_entries SET status=?, error_remark=?, updated_at=CURRENT_TIMESTAMP WHERE serial_number=?", (status,error,serial)); c.commit()

def get_entry(c, serial): return c.execute("SELECT * FROM playlist_entries WHERE serial_number=?", (serial,)).fetchone()

def existing_isrc(c, isrc):
    if not isrc: return None
    return c.execute("SELECT * FROM songs WHERE isrc=? LIMIT 1", (isrc,)).fetchone()
