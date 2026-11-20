#!/usr/bin/env python3
"""Step 1 - search YouTube for each YouTuber's videos and store their metadata.

Each search costs ~100 units of the 10,000-unit daily YouTube API quota.

Examples:
  python scripts/01_collect_videos.py --youtuber joseph
  python scripts/01_collect_videos.py --youtuber all --keywords stock investing --max-results 20
  python scripts/01_collect_videos.py --youtuber henry --all-tags
"""

import argparse
import os
import time

from dotenv import load_dotenv

from youtuber_analysis import config, db
from youtuber_analysis.collect.youtube import YouTubeClient


def main() -> None:
    cfg = config.settings()["collection"]
    keys = list(config.youtubers())
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--youtuber", choices=[*keys, "all"], required=True)
    parser.add_argument("--keywords", nargs="+", default=["stock"],
                        help="keywords appended to the YouTuber name (default: stock)")
    parser.add_argument("--all-tags", action="store_true",
                        help="use every tag in config/search_tags.txt as a keyword")
    parser.add_argument("--max-results", type=int, default=cfg["max_results_per_search"])
    parser.add_argument("--min-age", type=int, default=cfg["min_video_age_years"],
                        help="only videos at least this many years old")
    parser.add_argument("--db", default=str(config.MASTER_DB))
    args = parser.parse_args()

    load_dotenv()
    client = YouTubeClient(os.getenv("YOUTUBE_API_KEY", ""))
    keywords = config.search_tags() if args.all_tags else args.keywords
    db.init_db(args.db)

    with db.connect(args.db) as conn:
        for key in config.resolve_choice(args.youtuber, keys):
            yt = config.youtubers()[key]
            youtuber_id = db.insert_youtuber(conn, yt.channel_name)
            for kw in keywords:
                query = f"{yt.name} {kw}"
                ids = client.search_videos(query, args.max_results, args.min_age)
                new = 0
                for video in client.get_video_details(ids):
                    video.update(search_keyword=query, youtuber_id=youtuber_id)
                    new += db.insert_video(conn, video)
                conn.commit()
                print(f"[{key}] '{query}': {len(ids)} found, {new} new")
                time.sleep(cfg["youtube_delay_seconds"])
        print(db.statistics(conn))


if __name__ == "__main__":
    main()
