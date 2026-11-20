"""Project paths and configuration loaded from ``config/*.yaml``."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"

# Master database: every analysed video/stock pair for all YouTubers.
MASTER_DB = RAW_DIR / "youtube_analysis.db"


@dataclass(frozen=True)
class Youtuber:
    key: str
    name: str
    channel_name: str


def _load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def settings() -> dict:
    return _load_yaml("settings.yaml")


@lru_cache
def youtubers() -> dict[str, Youtuber]:
    items = _load_yaml("youtubers.yaml")["youtubers"]
    return {y["key"]: Youtuber(**y) for y in items}


def periods() -> dict[str, int]:
    """Period name -> number of months, e.g. ``{"1month": 1, ..., "2years": 24}``."""
    return dict(settings()["periods"])


def search_tags() -> list[str]:
    text = (CONFIG_DIR / "search_tags.txt").read_text(encoding="utf-8")
    return [t.strip() for t in text.split(",") if t.strip()]


def period_db_path(youtuber_key: str, period: str) -> Path:
    """Per-YouTuber, per-period database, e.g. ``data/interim/joseph/1year.db``."""
    return INTERIM_DIR / youtuber_key / f"{period}.db"


def processed_path(youtuber_key: str, period: str) -> Path:
    """Model-ready Excel file, e.g. ``data/processed/joseph_1year.xlsx``."""
    return PROCESSED_DIR / f"{youtuber_key}_{period}.xlsx"


def resolve_choice(value: str, choices: list[str]) -> list[str]:
    """Expand ``"all"`` to every choice; otherwise return ``[value]``."""
    return list(choices) if value == "all" else [value]
