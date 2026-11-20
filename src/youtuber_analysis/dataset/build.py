"""Build one database per (YouTuber, evaluation period).

Starting from the master database, keep only one YouTuber's rows and
recompute ``return_rate``, ``class`` and ``during`` for the given horizon.
Rows whose return cannot be computed (future date, missing price) are dropped.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from dateutil.relativedelta import relativedelta

from ..market.labeling import prediction_class
from ..market.prices import parse_date
from .comments import ScoreMap, apply_scores


class ReturnSource(Protocol):
    def period_return(self, ticker: str, start: date, months: int) -> float | None: ...


@dataclass
class BuildStats:
    computed: int = 0
    failed: int = 0
    future: int = 0
    kept: int = 0
    comment_scores_restored: int = 0


def relabel_period_db(db_path: str | Path, threshold: float = 0.05) -> int:
    """Recompute ``class`` from the stored ``return_rate`` (no price download).

    Returns the number of rows whose label changed.
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, video_sentiment, return_rate, class FROM Youtuber_Financial_Data "
            "WHERE return_rate IS NOT NULL"
        ).fetchall()
        changed = 0
        for row_id, sentiment, ret, old in rows:
            new = prediction_class(sentiment, ret, threshold)
            if new != old:
                conn.execute("UPDATE Youtuber_Financial_Data SET class = ? WHERE id = ?", (new, row_id))
                changed += 1
        conn.commit()
        return changed
    finally:
        conn.close()


def build_period_db(source_db: str | Path, target_db: str | Path, channel_name: str,
                    months: int, returns: ReturnSource, threshold: float = 0.05,
                    today: date | None = None,
                    comment_scores: ScoreMap | None = None) -> BuildStats:
    """``comment_scores`` - previously computed comment sentiment per
    (video_id, stock_ticker); written over the master values so a rebuild
    never loses them."""
    source_db, target_db = Path(source_db), Path(target_db)
    if not source_db.exists():
        raise FileNotFoundError(source_db)
    today = today or date.today()

    target_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_db, target_db)

    stats = BuildStats()
    conn = sqlite3.connect(target_db)
    try:
        conn.execute(
            "DELETE FROM Youtuber_Financial_Data WHERE video_id NOT IN "
            "(SELECT video_id FROM videos WHERE channel_name = ?)",
            (channel_name,),
        )
        if comment_scores:
            stats.comment_scores_restored = apply_scores(conn, comment_scores)
        rows = conn.execute(
            "SELECT id, stock_ticker, published_time, video_sentiment "
            "FROM Youtuber_Financial_Data WHERE stock_ticker IS NOT NULL"
        ).fetchall()

        for i, (row_id, ticker, published, sentiment) in enumerate(rows, 1):
            if i % 50 == 0:
                print(f"    {i}/{len(rows)}")
            ret = None
            try:
                pub = parse_date(published).date()
                end = pub + relativedelta(months=months)
                if end > today:
                    stats.future += 1
                else:
                    ret = returns.period_return(ticker, pub, months)
                    if ret is None:
                        stats.failed += 1
            except Exception as e:  # noqa: BLE001
                print(f"    {ticker} {published}: {e}")
                stats.failed += 1

            if ret is None:
                conn.execute(
                    "UPDATE Youtuber_Financial_Data SET return_rate = NULL, class = NULL WHERE id = ?",
                    (row_id,),
                )
                continue

            conn.execute(
                "UPDATE Youtuber_Financial_Data SET return_rate = ?, class = ?, during = ? WHERE id = ?",
                (ret, prediction_class(sentiment, ret, threshold), (end - pub).days, row_id),
            )
            stats.computed += 1

        conn.execute("DELETE FROM Youtuber_Financial_Data WHERE return_rate IS NULL")
        conn.commit()
        stats.kept = conn.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data").fetchone()[0]
    finally:
        conn.close()
    return stats
