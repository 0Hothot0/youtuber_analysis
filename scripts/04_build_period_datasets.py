#!/usr/bin/env python3
"""Step 4 - build one database per YouTuber and evaluation period.

For each (YouTuber, period) the master rows of that YouTuber are copied to
data/interim/<youtuber>/<period>.db and return_rate / class / during are
recomputed from Yahoo Finance prices for that horizon.

Examples:
  python scripts/04_build_period_datasets.py                       # all 5 x 5
  python scripts/04_build_period_datasets.py --youtuber joseph
  python scripts/04_build_period_datasets.py --youtuber henry --period 1year
"""

import argparse

from youtuber_analysis import config
from youtuber_analysis.dataset.build import build_period_db
from youtuber_analysis.market.prices import StockPriceFetcher


def main() -> None:
    keys, periods = list(config.youtubers()), config.periods()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--youtuber", choices=[*keys, "all"], default="all")
    parser.add_argument("--period", choices=[*periods, "all"], default="all")
    parser.add_argument("--source", default=str(config.MASTER_DB), help="master database")
    args = parser.parse_args()

    threshold = config.settings()["labeling"]["return_threshold"]
    fetcher = StockPriceFetcher()

    for key in config.resolve_choice(args.youtuber, keys):
        yt = config.youtubers()[key]
        for period in config.resolve_choice(args.period, list(periods)):
            target = config.period_db_path(key, period)
            print(f"{yt.name} / {period} -> {target.relative_to(config.PROJECT_ROOT)}")
            stats = build_period_db(args.source, target, yt.channel_name, periods[period],
                                    fetcher, threshold)
            print(f"  {stats}")


if __name__ == "__main__":
    main()
