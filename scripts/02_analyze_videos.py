#!/usr/bin/env python3
"""Step 2 - analyse unprocessed videos with Gemini and store one row per primary stock.

Requires GOOGLE_CLOUD_PROJECT (and Vertex AI credentials) in .env.

Examples:
  python scripts/02_analyze_videos.py --limit 20
  python scripts/02_analyze_videos.py --youtuber tom_nash --limit 5
  python scripts/02_analyze_videos.py --video-id dQw4w9WgXcQ
"""

import argparse
import os
import time

from dotenv import load_dotenv

from youtuber_analysis import config, db
from youtuber_analysis.analyze.gemini import GeminiVideoAnalyzer, pending_videos, save_analyses


def main() -> None:
    cfg = config.settings()["collection"]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--youtuber", choices=list(config.youtubers()))
    parser.add_argument("--video-id", help="analyse a single video")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--model", default=cfg["gemini_model"])
    parser.add_argument("--db", default=str(config.MASTER_DB))
    args = parser.parse_args()

    load_dotenv()
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT is not set (see .env.example)")
    analyzer = GeminiVideoAnalyzer(project, os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"), args.model)

    with db.connect(args.db) as conn:
        if args.video_id:
            videos = conn.execute("SELECT video_id, url, title FROM videos WHERE video_id = ?",
                                  (args.video_id,)).fetchall()
        else:
            channel = config.youtubers()[args.youtuber].channel_name if args.youtuber else None
            videos = pending_videos(conn, args.limit, channel)

        print(f"{len(videos)} video(s) to analyse")
        for i, v in enumerate(videos, 1):
            print(f"[{i}/{len(videos)}] {v['title'][:70]}")
            analyses = analyzer.analyze_video(v["url"])
            print(f"  saved {save_analyses(conn, v['video_id'], analyses)} stock(s)")
            if i < len(videos):
                time.sleep(cfg["gemini_delay_seconds"])


if __name__ == "__main__":
    main()
