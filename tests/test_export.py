import pandas as pd
import pytest

from youtuber_analysis.dataset.export import TEST_SHEET, TRAIN_SHEET, export_excel, split_and_scale


def test_split_is_chronological_and_scaled_on_train():
    df = pd.DataFrame({"t": range(10), "x": [float(i) for i in range(10)], "class": [1, -1] * 5})
    train, test = split_and_scale(df, ["t", "x", "class"], ["x"], train_ratio=0.8)

    assert len(train) == 8 and len(test) == 2
    assert set(test["t"]) == {8, 9}                       # newest rows go to test
    assert train["x"].mean() == pytest.approx(0, abs=1e-12)
    assert test["x"].min() > train["x"].max()             # scaled with train statistics


def test_export_excel(master_db, tmp_path):
    out = tmp_path / "x.xlsx"
    n_train, n_test = export_excel(master_db, out, ["view_number", "video_sentiment"], "class",
                                   ["view_number"], train_ratio=0.75)
    sheets = pd.read_excel(out, sheet_name=None)
    assert (n_train, n_test) == (3, 1)
    assert list(sheets) == [TRAIN_SHEET, TEST_SHEET]
    assert list(sheets[TRAIN_SHEET].columns) == ["view_number", "video_sentiment", "class"]
