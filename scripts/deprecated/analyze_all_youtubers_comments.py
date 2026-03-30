#!/usr/bin/env python3
"""
為所有 YouTuber 的所有時期分析留言情緒
支援: Joseph, Tom Nash, Fin Tek, Henry, Paul
時期: 1month, 3months, 6months, 1year, 2years
"""

import os
import sys
import time
import sqlite3
import argparse
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.youtube_search import YouTubeSearcher
from core.gemini_analyzer import GeminiVideoAnalyzer
from dotenv import load_dotenv

load_dotenv()

# API 延遲設定
GEMINI_DELAY = 10
YOUTUBE_DELAY = 0.5

# 所有資料庫配置
ALL_DATABASES = {
    'joseph': {
        'name': 'Joseph Hogue',
        'folder': 'joseph',
        'suffix': 'joseph',
        'periods': ['1month', '3months', '6months', '1year', '2years']
    },
    'tomnash': {
        'name': 'Tom Nash',
        'folder': 'tom_nash',
        'suffix': 'tomnash',
        'periods': ['1month', '3months', '6months', '1year', '2years']
    },
    'fintek': {
        'name': 'Fin Tek',
        'folder': 'fin_tek',
        'suffix': 'fintek',
        'periods': ['1month', '3months', '6months', '1year', '2years']
    },
    'henry': {
        'name': 'Invest with Henry',
        'folder': 'invest_with_henry',
        'suffix': 'henry',
        'periods': ['1month', '3months', '6months', '1year', '2years']
    },
    'paul': {
        'name': 'Paul Thomas',
        'folder': 'paul_thomas',
        'suffix': 'paul',
        'periods': ['1month', '3months', '6months', '1year', '2years']
    }
}


class CommentAnalyzer:
    """留言情緒分析器"""

    def __init__(self, youtube: YouTubeSearcher, gemini: GeminiVideoAnalyzer, dry_run: bool = False):
        self.youtube = youtube
        self.gemini = gemini
        self.dry_run = dry_run
        self.stats = {
            'success': 0,
            'failed': 0,
            'comments_disabled': 0,
            'no_comments': 0,
            'api_errors': 0
        }

    def get_pending_videos(self, db_path: str) -> List[Tuple[str]]:
        """取得待處理的影片列表（去重）"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT video_id
            FROM Youtuber_Financial_Data
            WHERE comment_sentiment = 0 OR comment_sentiment IS NULL
            ORDER BY video_id
        """)

        videos = [row[0] for row in cursor.fetchall()]
        conn.close()
        return videos

    def analyze_video_comments(self, video_id: str) -> Optional[float]:
        """分析單一影片的留言情緒"""

        # 抓取留言
        try:
            comments = self.youtube.get_video_comments(video_id)
            time.sleep(YOUTUBE_DELAY)
        except Exception as e:
            error_msg = str(e).lower()
            if 'disabled' in error_msg or 'forbidden' in error_msg:
                self.stats['comments_disabled'] += 1
                return None
            else:
                self.stats['api_errors'] += 1
                print(f"      ✗ YouTube API 錯誤: {str(e)[:50]}")
                return None

        if not comments:
            self.stats['no_comments'] += 1
            return 0.0

        # 使用 Gemini 分析留言情緒
        try:
            sentiment = self.gemini.analyze_comment_sentiment(comments)
            time.sleep(GEMINI_DELAY)
            return sentiment
        except Exception as e:
            self.stats['api_errors'] += 1
            print(f"      ✗ Gemini API 錯誤: {str(e)[:50]}")
            return None

    def update_database(self, db_path: str, video_id: str, sentiment: float):
        """更新資料庫中該影片的所有記錄"""
        if self.dry_run:
            print(f"      [DRY-RUN] 將更新 video_id={video_id}, sentiment={sentiment:.2f}")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE Youtuber_Financial_Data
            SET comment_sentiment = ?
            WHERE video_id = ?
        """, (sentiment, video_id))

        updated = cursor.rowcount
        conn.commit()
        conn.close()

        print(f"      ✓ 已更新 {updated} 筆記錄")

    def process_database(self, db_path: str, db_name: str, limit: Optional[int] = None):
        """處理單一資料庫"""

        if not os.path.exists(db_path):
            print(f"  ✗ 資料庫不存在: {db_path}")
            return

        print(f"\n{'='*80}")
        print(f"處理: {db_name}")
        print(f"路徑: {db_path}")
        print(f"{'='*80}")

        # 取得待處理影片
        pending_videos = self.get_pending_videos(db_path)
        total = len(pending_videos)

        if total == 0:
            print("  ✓ 所有影片都已分析完成")
            return

        print(f"\n待處理影片: {total} 部")

        if limit:
            pending_videos = pending_videos[:limit]
            print(f"限制處理: {len(pending_videos)} 部")

        # 處理每個影片
        for idx, video_id in enumerate(pending_videos, 1):
            print(f"\n[{idx}/{len(pending_videos)}] 影片 ID: {video_id}")

            # 分析留言
            sentiment = self.analyze_video_comments(video_id)

            if sentiment is None:
                self.stats['failed'] += 1
                print(f"      ✗ 分析失敗")
                continue

            # 更新資料庫
            self.update_database(db_path, video_id, sentiment)
            self.stats['success'] += 1
            print(f"      ✓ 情緒分數: {sentiment:.2f}")

        # 顯示統計
        print(f"\n{'='*80}")
        print(f"處理完成: {db_name}")
        print(f"{'='*80}")
        print(f"成功: {self.stats['success']}")
        print(f"失敗: {self.stats['failed']}")
        print(f"留言關閉: {self.stats['comments_disabled']}")
        print(f"無留言: {self.stats['no_comments']}")
        print(f"API 錯誤: {self.stats['api_errors']}")


def main():
    parser = argparse.ArgumentParser(
        description="為所有 YouTuber 的 single database 分析留言情緒",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 分析單一 YouTuber 的所有時期
  python3 scripts/analyze_all_youtubers_comments.py --youtuber joseph

  # 分析單一 YouTuber 的特定時期
  python3 scripts/analyze_all_youtubers_comments.py --youtuber joseph --period 1year

  # 分析所有 YouTuber 的所有時期
  python3 scripts/analyze_all_youtubers_comments.py --youtuber all

  # 測試模式
  python3 scripts/analyze_all_youtubers_comments.py --youtuber joseph --period 1year --limit 5 --dry-run
        """
    )

    parser.add_argument(
        "--youtuber",
        choices=list(ALL_DATABASES.keys()) + ['all'],
        required=True,
        help="選擇 YouTuber (joseph, tomnash, fintek, henry, paul, all)"
    )

    parser.add_argument(
        "--period",
        choices=['1month', '3months', '6months', '1year', '2years', 'all'],
        default='all',
        help="選擇時期（預設: all）"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="限制每個資料庫處理的影片數量（測試用）"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="測試模式，不實際更新資料庫"
    )

    args = parser.parse_args()

    # 初始化 API
    print("初始化 API...")
    api_key = os.getenv('YOUTUBE_API_KEY')
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')

    if not api_key:
        print("錯誤: 未設定 YOUTUBE_API_KEY 環境變數")
        sys.exit(1)

    if not project_id:
        print("錯誤: 未設定 GOOGLE_CLOUD_PROJECT 環境變數")
        sys.exit(1)

    youtube = YouTubeSearcher(api_key)
    gemini = GeminiVideoAnalyzer(project_id, location)
    analyzer = CommentAnalyzer(youtube, gemini, args.dry_run)

    # 確定要處理的資料庫
    youtubers_to_process = []
    if args.youtuber == 'all':
        youtubers_to_process = list(ALL_DATABASES.keys())
    else:
        youtubers_to_process = [args.youtuber]

    # 處理每個 YouTuber
    for yt_key in youtubers_to_process:
        yt_config = ALL_DATABASES[yt_key]

        # 確定要處理的時期
        periods_to_process = []
        if args.period == 'all':
            periods_to_process = yt_config['periods']
        else:
            periods_to_process = [args.period]

        # 處理每個時期
        for period in periods_to_process:
            db_path = f"{yt_config['folder']}/youtube_analysis_{period}_single_{yt_config['suffix']}.db"
            db_name = f"{yt_config['name']} ({period})"

            analyzer.process_database(db_path, db_name, args.limit)

    # 總結
    print(f"\n{'='*80}")
    print("全部完成")
    print(f"{'='*80}")
    print(f"總成功: {analyzer.stats['success']}")
    print(f"總失敗: {analyzer.stats['failed']}")
    print(f"留言關閉: {analyzer.stats['comments_disabled']}")
    print(f"無留言: {analyzer.stats['no_comments']}")
    print(f"API 錯誤: {analyzer.stats['api_errors']}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
