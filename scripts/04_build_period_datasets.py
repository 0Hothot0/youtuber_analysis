#!/usr/bin/env python3
"""Step 4 - build one database per YouTuber and evaluation period.

For each (YouTuber, period) the master rows of that YouTuber are copied to
data/interim/<youtuber>/<period>.db and return_rate / class / during are
recomputed from Yahoo Finance prices for that horizon.

Comment-sentiment scores are never lost on a rebuild: scores already in the
period database (or, if it is missing, in data/processed/comment_sentiment.csv)
are carried over in place of the master database's values.

Examples:
  python scripts/04_build_period_datasets.py                       # all 5 x 5
  python scripts/04_build_period_datasets.py --youtuber joseph
  python scripts/04_build_period_datasets.py --youtuber henry --period 1year
  python scripts/04_build_period_datasets.py --relabel-only   # re-apply the label rule, no download
"""

import argparse

from youtuber_analysis import config
from youtuber_analysis.dataset.build import build_period_db, relabel_period_db
from youtuber_analysis.dataset.comments import read_backup, read_scores
from youtuber_analysis.market.prices import StockPriceFetcher


def main() -> None:
    keys, periods = list(config.youtubers()), config.periods()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--youtuber", choices=[*keys, "all"], default="all")
    parser.add_argument("--period", choices=[*periods, "all"], default="all")
    parser.add_argument("--source", default=str(config.MASTER_DB), help="master database")
    parser.add_argument("--relabel-only", action="store_true",
                        help="recompute class from the stored return_rate of existing period databases")
    args = parser.parse_args()

    threshold = config.settings()["labeling"]["return_threshold"]
    fetcher = None if args.relabel_only else StockPriceFetcher()

    for key in config.resolve_choice(args.youtuber, keys):
        yt = config.youtubers()[key]
        for period in config.resolve_choice(args.period, list(periods)):
            target = config.period_db_path(key, period)
            if args.relabel_only:
                if target.exists():
                    print(f"{yt.name} / {period}: {relabel_period_db(target, threshold)} label(s) changed")
                continue
            print(f"{yt.name} / {period} -> {target.relative_to(config.PROJECT_ROOT)}")
            scores = read_backup(config.COMMENT_SENTIMENT_CSV, key, period)
            scores.update(read_scores(target))  # existing database wins over the CSV
            stats = build_period_db(args.source, target, yt.channel_name, periods[period],
                                    fetcher, threshold, comment_scores=scores)
            print(f"  {stats}")


if __name__ == "__main__":
    main()
