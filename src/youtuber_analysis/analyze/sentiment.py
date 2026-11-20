"""Comment sentiment with VADER (free, runs locally, no API cost)."""

from __future__ import annotations

import sqlite3

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer: SentimentIntensityAnalyzer | None = None


def comment_sentiment(comments: list[str], max_lines: int = 50) -> float:
    """Mean VADER compound score (-1 to 1) of the first ``max_lines`` comment lines.

    Multi-line comments are split into lines before scoring, matching the
    procedure used to build the published dataset. No comments -> 0.0.
    """
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()

    lines = [ln.strip() for c in comments for ln in c.split("\n") if ln.strip()]
    scores = [_analyzer.polarity_scores(ln)["compound"] for ln in lines[:max_lines]]
    return sum(scores) / len(scores) if scores else 0.0


def pending_video_ids(conn: sqlite3.Connection) -> list[str]:
    """Videos whose comment sentiment has not been computed yet (0 or NULL)."""
    rows = conn.execute("""
        SELECT DISTINCT video_id FROM Youtuber_Financial_Data
        WHERE comment_sentiment = 0 OR comment_sentiment IS NULL
        ORDER BY video_id
    """).fetchall()
    return [r[0] for r in rows]


def save_comment_sentiment(conn: sqlite3.Connection, video_id: str, score: float) -> int:
    """Write the score to every stock row of the video; returns rows updated."""
    cur = conn.execute(
        "UPDATE Youtuber_Financial_Data SET comment_sentiment = ? WHERE video_id = ?",
        (score, video_id),
    )
    conn.commit()
    return cur.rowcount
