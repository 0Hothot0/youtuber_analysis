#!/usr/bin/env python3
"""
改進版 Single 資料庫留言情緒分析
特點：智能重試、進度保存、詳細報告、彈性資料庫選擇
"""

import os
import sys
import time
import sqlite3
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.youtube_search import YouTubeSearcher
from core.gemini_analyzer import GeminiVideoAnalyzer
from dotenv import load_dotenv

load_dotenv()

# API 延遲設定（秒）
GEMINI_DELAY = 10
YOUTUBE_DELAY = 0.5

# 進度檔案
PROGRESS_FILE = ".comment_analysis_progress.json"


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

    def get_pending_videos(self, db_path: str) -> List[Tuple[str, str]]:
        """取得待處理的影片列表"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT video_id, video_uuid
            FROM Youtuber_Financial_Data
            WHERE comment_sentiment = 0 OR comment_sentiment IS NULL
            ORDER BY video_id
        """)

        videos = cursor.fetchall()
        conn.close()
        return videos

    def analyze_video(self, video_id: str, video_uuid: str) -> Optional[float]:
        """
        分析單一影片的留言情緒

        Returns:
            float: 情緒分數 (-1 到 1)
            0.0: 無留言
            None: 留言關閉或分析失敗
        """
        print(f"\n  處理影片: {video_id} (UUID: {video_uuid[:8]}...)")

        # 步驟 1: 抓取留言
        print(f"    [1/2] 抓取留言...", end=" ")
        try:
            comments = self.youtube.get_video_comments(video_id)
        except Exception as e:
            print(f"失敗")
            print(f"    ✗ YouTube API 錯誤: {str(e)[:100]}")
            self.stats['api_errors'] += 1
            return None

        # 處理留言被關閉的情況
        if comments is None:
            print(f"留言已關閉")
            self.stats['comments_disabled'] += 1
            return None

        # 處理無留言的情況
        if not comments.strip():
            print(f"無留言")
            self.stats['no_comments'] += 1
            return 0.0

        comment_count = len(comments.split('\n'))
        print(f"找到 {comment_count} 則留言")

        time.sleep(YOUTUBE_DELAY)

        # 步驟 2: 分析情緒
        print(f"    [2/2] 分析情緒...", end=" ")
        try:
            sentiment = self.gemini.analyze_comment_sentiment(comments)
        except Exception as e:
            print(f"失敗")
            print(f"    ✗ Gemini API 錯誤: {str(e)[:100]}")
            self.stats['api_errors'] += 1
            return None

        if sentiment is None:
            print(f"失敗")
            self.stats['api_errors'] += 1
            return None

        print(f"完成 (分數: {sentiment:.3f})")
        time.sleep(GEMINI_DELAY)

        return sentiment

    def update_database(self, db_path: str, video_id: str, sentiment: Optional[float]) -> int:
        """更新資料庫中的 comment_sentiment"""
        if self.dry_run:
            return 0

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

        return updated

    def save_progress(self, db_name: str, processed_videos: set):
        """保存處理進度"""
        progress_data = {
            'db_name': db_name,
            'processed_videos': list(processed_videos),
            'stats': self.stats,
            'last_update': datetime.now().isoformat()
        }

        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress_data, f, indent=2)

    def load_progress(self, db_name: str) -> set:
        """載入處理進度"""
        if not os.path.exists(PROGRESS_FILE):
            return set()

        try:
            with open(PROGRESS_FILE, 'r') as f:
                progress_data = json.load(f)

            if progress_data.get('db_name') != db_name:
                return set()

            print(f"\n✓ 載入上次進度:")
            print(f"  - 已處理: {len(progress_data['processed_videos'])} 個影片")
            print(f"  - 上次更新: {progress_data['last_update']}")

            return set(progress_data['processed_videos'])

        except Exception as e:
            print(f"⚠ 無法載入進度檔案: {e}")
            return set()


def get_database_stats(db_path: str) -> Dict:
    """取得資料庫統計資訊"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN comment_sentiment = 0 OR comment_sentiment IS NULL THEN 1 END) as pending,
            COUNT(CASE WHEN comment_sentiment IS NOT NULL AND comment_sentiment != 0 THEN 1 END) as completed,
            COUNT(DISTINCT video_id) as unique_videos
        FROM Youtuber_Financial_Data
    """)

    result = cursor.fetchone()
    conn.close()

    return {
        'total': result[0],
        'pending': result[1],
        'completed': result[2],
        'unique_videos': result[3]
    }


def main():
    parser = argparse.ArgumentParser(
        description="改進版 Single 資料庫留言情緒分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 分析 joseph 資料庫（2年期）
  python3 scripts/analyze_single_comments_improved.py --db joseph_2years

  # 分析所有 single 資料庫
  python3 scripts/analyze_single_comments_improved.py --db all

  # 測試模式（不更新資料庫）
  python3 scripts/analyze_single_comments_improved.py --db joseph_2years --dry-run

  # 限制處理數量
  python3 scripts/analyze_single_comments_improved.py --db joseph_2years --limit 10
        """
    )

    parser.add_argument(
        "--db",
        choices=["joseph_2years", "joseph_3months", "single_2years", "single_3months", "all"],
        required=True,
        help="選擇要處理的資料庫"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="限制處理影片數量（用於測試）"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="測試模式（不更新資料庫）"
    )

    parser.add_argument(
        "--reset-progress",
        action="store_true",
        help="清除進度檔案，重新開始"
    )

    args = parser.parse_args()

    # 資料庫映射
    db_mapping = {
        "joseph_2years": "youtube_analysis_2years_single_joseph.db",
        "joseph_3months": "youtube_analysis_3months_single_joseph.db",
        "single_2years": "youtube_analysis_2years_single.db",
        "single_3months": "youtube_analysis_3months_single.db"
    }

    # 選擇資料庫
    if args.db == "all":
        databases = list(db_mapping.values())
    else:
        databases = [db_mapping[args.db]]

    # 檢查環境變數
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if not youtube_api_key:
        print("❌ 錯誤：未設定 YOUTUBE_API_KEY")
        return 1

    if not project_id:
        print("❌ 錯誤：未設定 GOOGLE_CLOUD_PROJECT")
        return 1

    try:
        # 初始化客戶端
        print("\n" + "="*80)
        print("Single 資料庫留言情緒分析 (改進版)")
        print("="*80)
        print("\n初始化 API 客戶端...", end=" ")

        youtube = YouTubeSearcher(youtube_api_key)

        # 嘗試初始化 Gemini（多區域回退）
        regions_to_try = [
            ("us-central1", "gemini-1.5-flash-001"),
            ("us-central1", "gemini-1.5-pro-001"),
            ("us-east4", "gemini-1.5-flash-001"),
            ("us-west1", "gemini-1.5-flash-001"),
        ]

        gemini = None
        for region, model in regions_to_try:
            try:
                test_gemini = GeminiVideoAnalyzer(
                    project_id=project_id,
                    location=region,
                    model=model
                )
                test_result = test_gemini.analyze_comment_sentiment("test")
                if test_result is not None:
                    gemini = test_gemini
                    print(f"完成")
                    print(f"  ✓ Gemini API: {region} / {model}")
                    break
            except:
                continue

        if not gemini:
            print("失敗")
            print("\n❌ 無法初始化 Gemini API")
            print("請檢查:")
            print("  1. Google Cloud 專案權限")
            print("  2. Vertex AI API 是否啟用")
            print("  3. 帳號配額是否足夠")
            return 1

        # 處理每個資料庫
        total_success = 0
        total_failed = 0

        for db_path in databases:
            if not os.path.exists(db_path):
                print(f"\n⚠ 資料庫不存在: {db_path}")
                continue

            print(f"\n" + "="*80)
            print(f"處理資料庫: {db_path}")
            print("="*80)

            # 顯示統計
            stats = get_database_stats(db_path)
            print(f"\n資料庫狀態:")
            print(f"  總記錄數: {stats['total']}")
            print(f"  唯一影片數: {stats['unique_videos']}")
            print(f"  待處理: {stats['pending']}")
            print(f"  已完成: {stats['completed']}")

            if stats['pending'] == 0:
                print(f"\n✓ 此資料庫已全部完成！")
                continue

            # 初始化分析器
            analyzer = CommentAnalyzer(youtube, gemini, args.dry_run)

            # 載入或清除進度
            if args.reset_progress and os.path.exists(PROGRESS_FILE):
                os.remove(PROGRESS_FILE)
                print(f"\n✓ 已清除進度檔案")

            processed_videos = analyzer.load_progress(db_path)

            # 取得待處理影片
            pending_videos = analyzer.get_pending_videos(db_path)

            # 過濾已處理的影片
            pending_videos = [(vid, uuid) for vid, uuid in pending_videos
                            if vid not in processed_videos]

            if args.limit:
                pending_videos = pending_videos[:args.limit]

            if not pending_videos:
                print(f"\n✓ 沒有待處理的影片！")
                continue

            print(f"\n待處理影片: {len(pending_videos)} 個")
            if args.dry_run:
                print(f"模式: 測試模式（不更新資料庫）")
            print(f"預計時間: 約 {len(pending_videos) * (GEMINI_DELAY + YOUTUBE_DELAY + 2) / 60:.1f} 分鐘")

            # 處理每部影片
            for idx, (video_id, video_uuid) in enumerate(pending_videos, 1):
                print(f"\n[{idx}/{len(pending_videos)}]", end="")

                sentiment = analyzer.analyze_video(video_id, video_uuid)

                # 更新資料庫
                if sentiment is not None or sentiment == 0.0:
                    updated = analyzer.update_database(db_path, video_id, sentiment)
                    if updated > 0:
                        print(f"    ✓ 更新 {updated} 筆記錄")
                        analyzer.stats['success'] += 1
                    processed_videos.add(video_id)
                else:
                    analyzer.stats['failed'] += 1

                # 定期保存進度（每 10 個影片）
                if idx % 10 == 0:
                    analyzer.save_progress(db_path, processed_videos)

            # 最終保存進度
            analyzer.save_progress(db_path, processed_videos)

            # 顯示統計
            print(f"\n" + "-"*80)
            print(f"資料庫處理完成: {db_path}")
            print(f"-"*80)
            print(f"成功: {analyzer.stats['success']}")
            print(f"失敗: {analyzer.stats['failed']}")
            print(f"留言關閉: {analyzer.stats['comments_disabled']}")
            print(f"無留言: {analyzer.stats['no_comments']}")
            print(f"API 錯誤: {analyzer.stats['api_errors']}")

            total_success += analyzer.stats['success']
            total_failed += analyzer.stats['failed']

        # 總結
        print(f"\n" + "="*80)
        print(f"所有資料庫處理完成")
        print(f"="*80)
        print(f"總計成功: {total_success}")
        print(f"總計失敗: {total_failed}")

        if total_success > 0 and not args.dry_run:
            print(f"\n✓ 已更新 comment_sentiment 欄位")

        print(f"="*80 + "\n")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ 使用者中斷執行")
        print("進度已保存，下次執行會自動續接")
        return 130

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
