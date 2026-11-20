"""Keep comment data safe.

* raw comment text is stored in the ``comments`` table (step 3);
* comment-sentiment scores of every period database are backed up to a
  tracked CSV (step 5) and carried over when a period database is rebuilt
  (step 4), so a rebuild never resets them to 0.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ScoreMap = dict[tuple[str, str], float]

CSV_FIELDS = ["youtuber", "period", "video_id", "stock_ticker", "published_time", "comment_sentiment"]


# ---------------------------------------------------------------- raw comments

def save_comments(conn: sqlite3.Connection, video_id: str, comments: list[str]) -> int:
    """Store comment text in relevance order; existing rows are kept."""
    cur = conn.executemany(
        "INSERT OR IGNORE INTO comments (video_id, comment_rank, text) VALUES (?, ?, ?)",
        [(video_id, rank, text) for rank, text in enumerate(comments, 1)],
    )
    conn.commit()
    return cur.rowcount


def load_comments(conn: sqlite3.Connection, video_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT text FROM comments WHERE video_id = ? ORDER BY comment_rank", (video_id,)
    ).fetchall()
    return [r[0] for r in rows]


# ------------------------------------------------------------ sentiment scores

def read_scores(db_path: str | Path) -> ScoreMap:
    """Non-zero comment-sentiment scores of a period database."""
    if not Path(db_path).exists():
        return {}
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT video_id, stock_ticker, comment_sentiment FROM Youtuber_Financial_Data "
            "WHERE comment_sentiment IS NOT NULL AND comment_sentiment != 0"
        ).fetchall()
    return {(v, t): s for v, t, s in rows}


def apply_scores(conn: sqlite3.Connection, scores: ScoreMap) -> int:
    """Write preserved scores back; returns rows updated."""
    updated = 0
    for (video_id, ticker), score in scores.items():
        updated += conn.execute(
            "UPDATE Youtuber_Financial_Data SET comment_sentiment = ? "
            "WHERE video_id = ? AND stock_ticker = ?",
            (score, video_id, ticker),
        ).rowcount
    return updated


def write_backup(db_paths: dict[tuple[str, str], Path], csv_path: str | Path) -> int:
    """Write the scores of all period databases, keyed by (youtuber, period), to one CSV.

    Rows already in the CSV for a (youtuber, period) whose database is missing
    are kept, so the backup never shrinks because a local file is absent.
    """
    old: dict[tuple[str, str], list[list]] = {}
    if Path(csv_path).exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                old.setdefault((row["youtuber"], row["period"]), []).append(
                    [row[c] for c in CSV_FIELDS])

    rows = []
    for (youtuber, period), db_path in sorted(db_paths.items()):
        if not Path(db_path).exists():
            rows.extend(old.get((youtuber, period), []))
            continue
        with sqlite3.connect(db_path) as conn:
            for video_id, ticker, published, score in conn.execute(
                "SELECT video_id, stock_ticker, published_time, comment_sentiment "
                "FROM Youtuber_Financial_Data ORDER BY published_time, video_id, stock_ticker"
            ):
                rows.append([youtuber, period, video_id, ticker, published, score])

    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_FIELDS)
        writer.writerows(rows)
    return len(rows)


def read_backup(csv_path: str | Path, youtuber: str, period: str) -> ScoreMap:
    """Non-zero scores for one (youtuber, period) from the backup CSV."""
    if not Path(csv_path).exists():
        return {}
    scores: ScoreMap = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["youtuber"] != youtuber or row["period"] != period:
                continue
            if row["comment_sentiment"] not in ("", "0", "0.0"):
                scores[(row["video_id"], row["stock_ticker"])] = float(row["comment_sentiment"])
    return scores
