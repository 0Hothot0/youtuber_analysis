import sqlite3

import pytest

from youtuber_analysis import db


@pytest.fixture
def master_db(tmp_path):
    """A tiny master database with two channels."""
    path = tmp_path / "master.db"
    db.init_db(path)
    with db.connect(path) as conn:
        videos = [
            ("v1", "Chan A", "2023-01-10 10:00:00"),
            ("v2", "Chan A", "2023-02-10 10:00:00"),
            ("v3", "Chan B", "2023-03-10 10:00:00"),
        ]
        for vid, chan, pub in videos:
            db.insert_video(conn, {"video_id": vid, "url": f"u/{vid}", "title": vid,
                                   "channel_name": chan, "published_at": pub})
        rows = [
            ("v1", "AAA", 0.8, "2023-01-10 10:00:00"),
            ("v1", "BBB", -0.5, "2023-01-10 10:00:00"),
            ("v2", "AAA", 0.0, "2023-02-10 10:00:00"),
            ("v3", "CCC", 0.6, "2023-03-10 10:00:00"),
        ]
        for i, (vid, ticker, sent, pub) in enumerate(rows):
            db.insert_analysis(conn, {"video_uuid": vid, "video_id": vid, "stock_ticker": ticker,
                                      "video_sentiment": sent, "published_time": pub,
                                      "view_number": 1000 * (i + 1)})
    return path


def read(path, sql):
    with sqlite3.connect(path) as conn:
        return conn.execute(sql).fetchall()
