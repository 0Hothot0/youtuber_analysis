#!/usr/bin/env python3
"""留言情緒分析器 - 使用 YouTube API + Gemini AI"""

import os
import sys
import time
import argparse
from typing import Optional
from dotenv import load_dotenv

from youtube_search import YouTubeSearcher
from gemini_analyzer import GeminiVideoAnalyzer
from db_manager import DatabaseManager

# 載入環境變數
load_dotenv()

# 常數
GEMINI_DELAY = 10  # Gemini API 間隔（秒）- 增加以避免配額限制
YOUTUBE_DELAY = 0.5  # YouTube API 間隔（秒）


def process_video(
    video_uuid: str,
    video_id: str,
    youtube: YouTubeSearcher,
    gemini: GeminiVideoAnalyzer,
    db: DatabaseManager,
    dry_run: bool = False
) -> bool:
    """
    處理單一影片：抓取留言、分析情緒、更新資料庫

    Args:
        video_uuid: 影片 UUID
        video_id: YouTube 影片 ID
        youtube: YouTube API 客戶端
        gemini: Gemini API 客戶端
        db: 資料庫管理器
        dry_run: 測試模式（不更新資料庫）

    Returns:
        True 成功，False 失敗
    """
    print(f"\n  處理影片: {video_id} (UUID: {video_uuid[:8]}...)")

    # 步驟 1: 抓取留言
    print(f"  抓取留言...")
    comments = youtube.get_video_comments(video_id)

    # 處理留言被關閉的情況
    if comments is None:
        print(f"  留言已關閉 - 設為 NULL")
        if not dry_run:
            updated = db.update_comment_sentiment_by_uuid(video_uuid, None)
            print(f"  更新 {updated} 筆記錄")
        return True

    # 處理無留言的情況
    if not comments.strip():
        print(f"  無留言 - 設為 0.0")
        if not dry_run:
            updated = db.update_comment_sentiment_by_uuid(video_uuid, 0.0)
            print(f"  更新 {updated} 筆記錄")
        return True

    comment_count = len(comments.split('\n'))
    print(f"  找到 {comment_count} 則留言 ({len(comments)} 字元)")

    # API 限速
    time.sleep(YOUTUBE_DELAY)

    # 步驟 2: 分析情緒
    print(f"  分析情緒...")
    sentiment = gemini.analyze_comment_sentiment(comments)

    if sentiment is None:
        print(f"  ✗ 情緒分析失敗")
        return False

    print(f"  情緒分數: {sentiment:.3f}")

    # 步驟 3: 更新資料庫
    if not dry_run:
        updated = db.update_comment_sentiment_by_uuid(video_uuid, sentiment)
        print(f"  更新 {updated} 筆記錄")
    else:
        print(f"  [測試模式] 將更新記錄，情緒分數: {sentiment:.3f}")

    # API 限速
    time.sleep(GEMINI_DELAY)

    return True


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(
        description="YouTube 留言情緒分析 - 使用 Gemini AI"
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="批次處理所有待分析影片"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="限制處理數量"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="測試模式（不更新資料庫）"
    )

    args = parser.parse_args()

    # 檢查參數
    if not args.batch:
        parser.print_help()
        print("\n錯誤：請使用 --batch 批次處理")
        return 1

    # 載入環境變數
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not youtube_api_key:
        print("❌ 錯誤：未設定 YOUTUBE_API_KEY")
        return 1

    if not project_id:
        print("❌ 錯誤：未設定 GOOGLE_CLOUD_PROJECT")
        return 1

    try:
        # 初始化客戶端
        print("\n初始化客戶端...")
        youtube = YouTubeSearcher(youtube_api_key)
        gemini = GeminiVideoAnalyzer(
            project_id=project_id,
            location=location
        )
        db = DatabaseManager()
        db.connect()

        # 取得待處理影片
        print("\n取得待處理影片清單...")
        pending = db.get_pending_video_uuids()

        if not pending:
            print("✓ 沒有待處理的影片（所有影片都已分析留言情緒）")
            db.close()
            return 0

        if args.limit:
            pending = pending[:args.limit]

        print(f"\n{'='*80}")
        print(f"留言情緒批次分析")
        print(f"{'='*80}")
        print(f"待處理影片: {len(pending)}")
        if args.dry_run:
            print(f"模式: 測試模式（不更新資料庫）")
        print(f"{'='*80}")

        # 處理每部影片
        success = 0
        failed = 0

        for idx, video in enumerate(pending, 1):
            print(f"\n[{idx}/{len(pending)}]", end="")
            result = process_video(
                video_uuid=video['video_uuid'],
                video_id=video['video_id'],
                youtube=youtube,
                gemini=gemini,
                db=db,
                dry_run=args.dry_run
            )

            if result:
                success += 1
            else:
                failed += 1

        # 顯示摘要
        print(f"\n\n{'='*80}")
        print(f"批次分析完成")
        print(f"{'='*80}")
        print(f"處理: {len(pending)} 部影片")
        print(f"成功: {success}")
        print(f"失敗: {failed}")
        print(f"{'='*80}\n")

        db.close()
        return 0

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
