#!/usr/bin/env python3
"""Step 0 - create the master database and seed YouTubers and search tags."""

import argparse

from youtuber_analysis import config, db


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(config.MASTER_DB), help="database path")
    args = parser.parse_args()

    db.init_db(args.db)
    with db.connect(args.db) as conn:
        for y in config.youtubers().values():
            db.insert_youtuber(conn, y.channel_name)
        for tag in config.search_tags():
            db.insert_tag(conn, tag)
        print(f"Initialised {args.db}: {db.statistics(conn)}")


if __name__ == "__main__":
    main()
