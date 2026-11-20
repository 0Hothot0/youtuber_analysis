"""SQLite storage for videos and their Gemini analyses."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS youtubers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS search_tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tag         TEXT NOT NULL UNIQUE,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS videos (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id          TEXT UNIQUE NOT NULL,
    url               TEXT NOT NULL,
    title             TEXT NOT NULL,
    channel_name      TEXT,
    channel_id        TEXT,
    description       TEXT,
    published_at      TEXT,
    view_count        INTEGER DEFAULT 0,
    like_count        INTEGER DEFAULT 0,
    comment_count     INTEGER DEFAULT 0,
    duration          TEXT,
    thumbnail_default TEXT,
    thumbnail_medium  TEXT,
    thumbnail_high    TEXT,
    search_keyword    TEXT,
    youtuber_id       INTEGER,
    created_at        TEXT DEFAULT (datetime('now')),
    updated_at        TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (youtuber_id) REFERENCES youtubers(id)
);
CREATE INDEX IF NOT EXISTS idx_videos_channel_id   ON videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at);
CREATE INDEX IF NOT EXISTS idx_videos_youtuber_id  ON videos(youtuber_id);

-- One row per (video, primary stock) pair.
CREATE TABLE IF NOT EXISTS Youtuber_Financial_Data (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    video_uuid                TEXT NOT NULL,   -- shared by all stocks of one video
    video_id                  TEXT NOT NULL,
    stock_ticker              TEXT,
    like_number               INTEGER,
    comment_number            INTEGER,
    view_number               INTEGER,
    text_type                 INTEGER,
    video_sentiment           REAL,
    comment_sentiment         REAL DEFAULT 0,
    financial_ratio           REAL,
    celebrity                 INTEGER,
    relevancy                 REAL,
    published_time            TEXT,
    long_term_competitiveness INTEGER,
    short_term_focus          INTEGER,
    ceo_leadership_style      INTEGER,
    earnings_expectation_gap  REAL,
    stock_price_growth_trend  REAL,
    market_demand             REAL,
    market_capitalization     INTEGER,
    target_price              INTEGER,
    financial_health          REAL,
    valuation                 REAL,
    policy_impact             REAL,
    raw_json                  TEXT,
    return_rate               REAL DEFAULT NULL,
    class                     INTEGER DEFAULT NULL,
    youtuber                  TEXT,
    created_at                TEXT DEFAULT (datetime('now')),
    updated_at                TEXT DEFAULT (datetime('now')),
    during                    INTEGER,          -- days between publish and evaluation date
    UNIQUE(video_id, stock_ticker),
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);
"""

ANALYSIS_FIELDS = [
    "video_uuid", "video_id", "stock_ticker", "like_number", "comment_number",
    "view_number", "text_type", "video_sentiment", "comment_sentiment",
    "financial_ratio", "celebrity", "relevancy", "published_time",
    "long_term_competitiveness", "short_term_focus", "ceo_leadership_style",
    "earnings_expectation_gap", "stock_price_growth_trend", "market_demand",
    "market_capitalization", "target_price", "financial_health", "valuation",
    "policy_impact", "raw_json", "youtuber",
]

VIDEO_FIELDS = [
    "video_id", "url", "title", "channel_name", "channel_id", "description",
    "published_at", "view_count", "like_count", "comment_count", "duration",
    "thumbnail_default", "thumbnail_medium", "thumbnail_high",
    "search_keyword", "youtuber_id",
]


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a database with rows accessible by column name."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path) -> None:
    """Create all tables (no-op for tables that already exist)."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def _insert_unique(conn: sqlite3.Connection, table: str, column: str, value: str) -> int:
    conn.execute(f"INSERT OR IGNORE INTO {table} ({column}) VALUES (?)", (value,))
    return conn.execute(f"SELECT id FROM {table} WHERE {column} = ?", (value,)).fetchone()[0]


def insert_youtuber(conn: sqlite3.Connection, name: str) -> int:
    return _insert_unique(conn, "youtubers", "name", name)


def insert_tag(conn: sqlite3.Connection, tag: str) -> int:
    return _insert_unique(conn, "search_tags", "tag", tag.strip())


def find_youtuber_id(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM youtubers WHERE lower(name) = lower(?)", (name,)
    ).fetchone()
    return row[0] if row else None


def insert_video(conn: sqlite3.Connection, video: dict[str, Any]) -> bool:
    """Insert a video; returns False if it already exists."""
    cur = conn.execute(
        f"INSERT OR IGNORE INTO videos ({', '.join(VIDEO_FIELDS)}) "
        f"VALUES ({', '.join('?' * len(VIDEO_FIELDS))})",
        [video.get(f) for f in VIDEO_FIELDS],
    )
    return cur.rowcount > 0


def insert_analysis(conn: sqlite3.Connection, row: dict[str, Any]) -> bool:
    """Insert one (video, stock) analysis; returns False on duplicate."""
    cur = conn.execute(
        f"INSERT OR IGNORE INTO Youtuber_Financial_Data ({', '.join(ANALYSIS_FIELDS)}) "
        f"VALUES ({', '.join('?' * len(ANALYSIS_FIELDS))})",
        [row.get(f) for f in ANALYSIS_FIELDS],
    )
    return cur.rowcount > 0


def statistics(conn: sqlite3.Connection) -> dict[str, int]:
    tables = {
        "youtubers": "youtubers",
        "tags": "search_tags",
        "videos": "videos",
        "analyses": "Youtuber_Financial_Data",
    }
    return {k: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for k, t in tables.items()}
