#!/usr/bin/env python3
"""Step 5 - export each period database to a train/test Excel file.

Output: data/processed/<youtuber>_<period>.xlsx with sheets Training_Data and
Test_Data (12 features + class; see docs/data_dictionary.md).

Examples:
  python scripts/05_export_excel.py
  python scripts/05_export_excel.py --youtuber fin_tek --period 2years
"""

import argparse

from youtuber_analysis import config
from youtuber_analysis.dataset.export import export_excel


def main() -> None:
    keys, periods = list(config.youtubers()), list(config.periods())
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--youtuber", choices=[*keys, "all"], default="all")
    parser.add_argument("--period", choices=[*periods, "all"], default="all")
    args = parser.parse_args()

    ds = config.settings()["dataset"]
    for key in config.resolve_choice(args.youtuber, keys):
        for period in config.resolve_choice(args.period, periods):
            src = config.period_db_path(key, period)
            if not src.exists():
                print(f"skip {key}/{period}: {src} not found (run step 4 first)")
                continue
            out = config.processed_path(key, period)
            n_train, n_test = export_excel(src, out, ds["features"], ds["target"], ds["standardize"],
                                           ds["train_ratio"], ds["random_state"])
            print(f"{out.name}: train={n_train} test={n_test}")


if __name__ == "__main__":
    main()
