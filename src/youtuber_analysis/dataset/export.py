"""Turn a period database into a model-ready Excel file.

* chronological split: earliest ``train_ratio`` of rows -> train, rest -> test
  (no look-ahead: every test video is newer than every training video)
* rows are shuffled within each split
* engagement counts are z-scored with a scaler fitted on the training split
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
from sklearn.preprocessing import StandardScaler

TRAIN_SHEET = "Training_Data"
TEST_SHEET = "Test_Data"


def load_rows(db_path: str | Path, columns: list[str]) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(
            f"SELECT {', '.join(columns)}, published_time "
            "FROM Youtuber_Financial_Data ORDER BY published_time",
            conn,
        )


def split_and_scale(df: pd.DataFrame, columns: list[str], standardize: list[str],
                    train_ratio: float = 0.8, random_state: int = 42
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``df`` must already be sorted by publish time."""
    split = int(len(df) * train_ratio)
    train = df.iloc[:split][columns].sample(frac=1, random_state=random_state).reset_index(drop=True)
    test = df.iloc[split:][columns].sample(frac=1, random_state=random_state).reset_index(drop=True)

    cols = [c for c in standardize if c in columns]
    if cols and len(train):
        scaler = StandardScaler().fit(train[cols])
        train[cols] = scaler.transform(train[cols])
        if len(test):
            test[cols] = scaler.transform(test[cols])
    return train, test


def export_excel(db_path: str | Path, output: str | Path, features: list[str], target: str,
                 standardize: list[str], train_ratio: float = 0.8,
                 random_state: int = 42) -> tuple[int, int]:
    columns = [*features, target]
    df = load_rows(db_path, columns)
    train, test = split_and_scale(df, columns, standardize, train_ratio, random_state)

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        train.to_excel(writer, sheet_name=TRAIN_SHEET, index=False)
        test.to_excel(writer, sheet_name=TEST_SHEET, index=False)
    return len(train), len(test)
