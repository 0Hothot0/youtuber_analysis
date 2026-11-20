#!/usr/bin/env python3
"""Step 3 - score each video's top comments with VADER and store comment_sentiment.

Runs on the master database by default, so every period database built in
step 4 inherits the same score. Pass --db to update another database.

Examples:
  python scripts/03_comment_sentiment.py
  python scripts/03_comment_sentiment.py --limit 3 --dry-run
  python scripts/03_comment_sentiment.py --db data/interim/joseph/1year.db
"""

import argparse
import os
import time

from dotenv import load_dotenv

from youtuber_analysis import config, db
from youtuber_analysis.analyze.sentiment import comment_sentiment, pending_video_ids, save_comment_sentiment
from youtuber_analysis.collect.youtube import YouTubeClient


def main() -> None:
    cfg = config.settings()["collection"]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=str(config.MASTER_DB))
    parser.add_argument("--limit", type=int, help="process at most N videos")
    parser.add_argument("--dry-run", action="store_true", help="do not write to the database")
    args = parser.parse_args()

    load_dotenv()
    client = YouTubeClient(os.getenv("YOUTUBE_API_KEY", ""))

    with db.connect(args.db) as conn:
        video_ids = pending_video_ids(conn)[: args.limit]
        print(f"{len(video_ids)} video(s) pending in {args.db}")
        ok = failed = 0
        for i, vid in enumerate(video_ids, 1):
            comments = client.get_video_comments(vid, max_comments=cfg["max_comments"])
            time.sleep(cfg["youtube_delay_seconds"])
            if comments is None:
                failed += 1
                print(f"[{i}/{len(video_ids)}] {vid}: comments unavailable")
                continue
            score = comment_sentiment(comments, cfg["max_comments"])
            n = 0 if args.dry_run else save_comment_sentiment(conn, vid, score)
            ok += 1
            print(f"[{i}/{len(video_ids)}] {vid}: {score:+.3f} ({n} rows)")
        print(f"done: {ok} scored, {failed} unavailable")


if __name__ == "__main__":
    main()
