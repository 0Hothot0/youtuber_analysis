import csv
import sqlite3
from datetime import date

from conftest import read

from youtuber_analysis import db
from youtuber_analysis.dataset.build import build_period_db
from youtuber_analysis.dataset.comments import (load_comments, read_backup, read_scores,
                                                save_comments, write_backup)


class FlatReturns:
    def period_return(self, ticker, start, months):
        return 0.10


def test_comments_round_trip(master_db):
    with db.connect(master_db) as conn:
        assert save_comments(conn, "v1", ["first", "second\nline"]) == 2
        save_comments(conn, "v1", ["changed"])            # existing rows are never overwritten
        assert load_comments(conn, "v1") == ["first", "second\nline"]
        assert load_comments(conn, "v2") == []


def test_rebuild_keeps_comment_scores(master_db, tmp_path):
    target = tmp_path / "a.db"
    build_period_db(master_db, target, "Chan A", 3, FlatReturns(), today=date(2025, 1, 1))
    with sqlite3.connect(target) as conn:                 # scores computed after the first build
        conn.execute("UPDATE Youtuber_Financial_Data SET comment_sentiment = 0.42 WHERE video_id = 'v1'")

    saved = read_scores(target)
    stats = build_period_db(master_db, target, "Chan A", 3, FlatReturns(),
                            today=date(2025, 1, 1), comment_scores=saved)

    assert stats.comment_scores_restored == 2
    assert read(target, "SELECT video_id, comment_sentiment FROM Youtuber_Financial_Data ORDER BY id") == \
        [("v1", 0.42), ("v1", 0.42), ("v2", None)]


def test_backup_csv_round_trip_and_never_shrinks(master_db, tmp_path):
    period_db = tmp_path / "a.db"
    build_period_db(master_db, period_db, "Chan A", 3, FlatReturns(), today=date(2025, 1, 1))
    with sqlite3.connect(period_db) as conn:
        conn.execute("UPDATE Youtuber_Financial_Data SET comment_sentiment = 0.5 WHERE video_id = 'v2'")

    backup = tmp_path / "scores.csv"
    assert write_backup({("a", "3months"): period_db}, backup) == 3
    assert read_backup(backup, "a", "3months") == {("v2", "AAA"): 0.5}

    period_db.unlink()                                    # local database lost
    assert write_backup({("a", "3months"): period_db}, backup) == 3
    with open(backup, newline="") as f:
        assert len(list(csv.DictReader(f))) == 3
