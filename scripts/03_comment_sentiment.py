#!/usr/bin/env python3
"""Step 3 - fetch each video's top comments, save the text, score them with VADER.

The raw comment text is stored in the ``comments`` table so it can be re-scored
later without calling the API again (--rescore). The score goes to
Youtuber_Financial_Data.comment_sentiment.

Runs on the master database by default, so every period database built in
step 4 inherits the same score. Pass --db to update another database.

Examples:
  python scripts/03_comment_sentiment.py
  python scripts/03_comment_sentiment.py --limit 3 --dry-run
  python scripts/03_comment_sentiment.py --db data/interim/joseph/1year.db
  python scripts/03_comment_sentiment.py --rescore      # re-score saved comments, no API calls
"""

import argparse
import os
import time

from dotenv import load_dotenv

from youtuber_analysis import config, db
from youtuber_analysis.analyze.sentiment import comment_sentiment, pending_video_ids, save_comment_sentiment
from youtuber_analysis.collect.youtube import YouTubeClient
from youtuber_analysis.dataset.comments import load_comments, save_comments


def main() -> None:
    cfg = config.settings()["collection"]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=str(config.MASTER_DB))
    parser.add_argument("--limit", type=int, help="process at most N videos")
    parser.add_argument("--dry-run", action="store_true", help="do not write to the database")
    parser.add_argument("--rescore", action="store_true",
                        help="re-score every video that has saved comments (no API calls)")
    args = parser.parse_args()

    db.init_db(args.db)  # adds the comments table to older databases
    client = None
    if not args.rescore:
        load_dotenv()
        client = YouTubeClient(os.getenv("YOUTUBE_API_KEY", ""))

    with db.connect(args.db) as conn:
        if args.rescore:
            video_ids = [r[0] for r in conn.execute("SELECT DISTINCT video_id FROM comments ORDER BY video_id")]
        else:
            video_ids = pending_video_ids(conn)
        video_ids = video_ids[: args.limit]
        print(f"{len(video_ids)} video(s) to score in {args.db}")
        ok = failed = 0
        for i, vid in enumerate(video_ids, 1):
            comments = load_comments(conn, vid)
            if not comments and client is not None:
                comments = client.get_video_comments(vid, max_comments=cfg["max_comments"])
                time.sleep(cfg["youtube_delay_seconds"])
                if comments and not args.dry_run:
                    save_comments(conn, vid, comments)
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
