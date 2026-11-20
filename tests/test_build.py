from datetime import date

from conftest import read

from youtuber_analysis.dataset.build import build_period_db


class FakeReturns:
    def __init__(self, table):
        self.table = table

    def period_return(self, ticker, start, months):
        return self.table.get(ticker)


def test_build_filters_channel_and_labels(master_db, tmp_path):
    target = tmp_path / "out" / "a_3m.db"
    returns = FakeReturns({"AAA": 0.10, "BBB": None})  # BBB price missing -> dropped
    stats = build_period_db(master_db, target, "Chan A", 3, returns, today=date(2025, 1, 1))

    rows = read(target, "SELECT video_id, stock_ticker, return_rate, class, during "
                        "FROM Youtuber_Financial_Data ORDER BY video_id")
    assert rows == [
        ("v1", "AAA", 0.10, 1, 90),    # bullish + 10%  -> correct
        ("v2", "AAA", 0.10, -1, 89),   # neutral + 10%  -> wrong
    ]
    assert (stats.computed, stats.failed, stats.kept) == (2, 1, 2)


def test_build_drops_future_horizons(master_db, tmp_path):
    target = tmp_path / "a_24m.db"
    stats = build_period_db(master_db, target, "Chan A", 24, FakeReturns({"AAA": 0.1, "BBB": 0.1}),
                            today=date(2024, 1, 15))
    assert stats.future == 3 and stats.kept == 0


def test_relabel_fixes_wrong_labels(master_db, tmp_path):
    from conftest import read
    from youtuber_analysis.dataset.build import relabel_period_db
    import sqlite3

    target = tmp_path / "a.db"
    build_period_db(master_db, target, "Chan A", 3, FakeReturns({"AAA": 0.10, "BBB": -0.10}),
                    today=date(2025, 1, 1))
    with sqlite3.connect(target) as conn:            # corrupt: label = "return > 0"
        conn.execute("UPDATE Youtuber_Financial_Data SET class = CASE WHEN return_rate > 0 THEN 1 ELSE -1 END")
    assert relabel_period_db(target) == 2            # v1/BBB (bearish, -10%) and v2/AAA (neutral, +10%)
    assert read(target, "SELECT class FROM Youtuber_Financial_Data ORDER BY id") == [(1,), (1,), (-1,)]
