#!/usr/bin/env python3
"""
分析 Joseph Hogue 數據庫的評論情感
支持 2years 和 3months 版本
"""

import os
import sys
import time
import sqlite3
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.youtube_search import YouTubeSearcher
from core.gemini_analyzer import GeminiVideoAnalyzer
from dotenv import load_dotenv

load_dotenv()

GEMINI_DELAY = 10  # Gemini API 間隔（秒）
YOUTUBE_DELAY = 0.5  # YouTube API 間隔（秒）


def get_unique_videos(db_path):
    """獲取數據庫中需要分析的唯一 video_id 列表"""
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


def analyze_video_comments(video_id, video_uuid, youtube, gemini):
    """分析單個視頻的評論情感"""
    print(f"\n  處理視頻: {video_id} (UUID: {video_uuid[:8]}...)")

    # 步驟1: 抓取評論
    print(f"  抓取評論...")
    try:
        comments = youtube.get_video_comments(video_id)
    except Exception as e:
        print(f"  ✗ 抓取失敗: {str(e)[:100]}")
        return None

    # 處理留言被關閉的情況
    if comments is None:
        print(f"  留言已關閉 - 返回 None")
        return None

    # 處理無留言的情況
    if not comments.strip():
        print(f"  無留言 - 返回 0.0")
        return 0.0

    comment_count = len(comments.split('\n'))
    print(f"  找到 {comment_count} 則留言 ({len(comments)} 字符)")

    time.sleep(YOUTUBE_DELAY)

    # 步驟2: 分析情緒
    print(f"  分析情緒...")
    try:
        sentiment = gemini.analyze_comment_sentiment(comments)
    except Exception as e:
        print(f"  ✗ 分析失敗: {str(e)[:100]}")
        return None

    if sentiment is None:
        print(f"  ✗ 情緒分析失敗")
        return None

    print(f"  情緒分數: {sentiment:.3f}")
    time.sleep(GEMINI_DELAY)

    return sentiment


def update_comment_sentiment(db_path, video_id, sentiment):
    """更新數據庫中指定 video_id 的所有記錄的 comment_sentiment"""
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


def get_database_stats(db_path):
    """獲取數據庫統計信息"""
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT video_id) as unique_videos,
            SUM(CASE WHEN comment_sentiment = 0 THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN comment_sentiment IS NULL THEN 1 ELSE 0 END) as null_count,
            SUM(CASE WHEN comment_sentiment > 0 OR comment_sentiment < 0 THEN 1 ELSE 0 END) as analyzed
        FROM Youtuber_Financial_Data
    """)

    result = cursor.fetchone()
    conn.close()

    return {
        'total': result[0],
        'unique_videos': result[1],
        'pending': result[2],
        'null': result[3],
        'analyzed': result[4]
    }


def main():
    parser = argparse.ArgumentParser(
        description="分析 Joseph Hogue 數據庫的評論情感"
    )

    parser.add_argument(
        "--database",
        choices=["2years", "3months", "both"],
        default="both",
        help="選擇要處理的數據庫 (預設: both)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="限制處理視頻數量（用於測試）"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="測試模式（不更新數據庫）"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="繼續未完成的分析"
    )

    args = parser.parse_args()

    # 檢查環境變量
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
        # 確定要處理的數據庫
        db_list = []
        if args.database in ["2years", "both"]:
            db_list.append("youtube_analysis_2years_single_joseph.db")
        if args.database in ["3months", "both"]:
            db_list.append("youtube_analysis_3months_single_joseph.db")

        # 檢查數據庫是否存在
        for db in db_list:
            if not os.path.exists(db):
                print(f"❌ 數據庫不存在: {db}")
                return 1

        # 顯示當前狀態
        print("\n" + "="*80)
        print("Joseph Hogue 評論情感分析工具")
        print("="*80)

        for db in db_list:
            stats = get_database_stats(db)
            if stats:
                print(f"\n{db}:")
                print(f"  總記錄: {stats['total']}")
                print(f"  唯一視頻: {stats['unique_videos']}")
                print(f"  待分析: {stats['pending']}")
                print(f"  已分析: {stats['analyzed']}")
                print(f"  無評論: {stats['null']}")

        print("="*80)

        # 初始化客戶端
        print("\n初始化客戶端...")
        youtube = YouTubeSearcher(youtube_api_key)

        # 嘗試多個區域和模型組合
        regions_to_try = [
            ("us-central1", "gemini-1.5-flash-001"),
            ("us-central1", "gemini-1.5-pro-001"),
            ("us-east4", "gemini-1.5-flash-001"),
            ("us-west1", "gemini-1.5-flash-001"),
        ]

        gemini = None
        print("\n測試 Gemini API 連接...")
        for region, model in regions_to_try:
            try:
                print(f"  嘗試區域: {region}, 模型: {model}")
                test_gemini = GeminiVideoAnalyzer(
                    project_id=project_id,
                    location=region,
                    model=model
                )
                # 簡單測試
                test_result = test_gemini.analyze_comment_sentiment("test comment")
                if test_result is not None:
                    gemini = test_gemini
                    print(f"  ✓ 成功！使用區域: {region}, 模型: {model}")
                    break
            except Exception as e:
                print(f"    ✗ 失敗: {str(e)[:80]}")
                continue

        if not gemini:
            print("\n❌ 無法找到可用的 Gemini 配置")
            print("\n請檢查:")
            print("  1. Google Cloud 項目權限")
            print("  2. Vertex AI API 是否啟用")
            print("  3. 帳戶是否有足夠的配額")
            print("\n💡 提示: 當 API 更新後，請重新運行此腳本")
            return 1

        # 收集所有需要分析的視頻
        all_videos = {}

        for db in db_list:
            videos = get_unique_videos(db)
            print(f"\n{db}: {len(videos)} 個視頻需要分析")

            for video_id, video_uuid in videos:
                if video_id not in all_videos:
                    all_videos[video_id] = video_uuid

        if not all_videos:
            print("\n✓ 所有視頻都已分析完成！")
            return 0

        video_list = list(all_videos.items())

        if args.limit:
            video_list = video_list[:args.limit]
            print(f"\n⚠️  限制處理數量: {args.limit} 個視頻")

        print(f"\n{'='*80}")
        print(f"開始批次分析")
        print(f"{'='*80}")
        print(f"待處理視頻: {len(video_list)} 個")
        print(f"目標數據庫: {', '.join([os.path.basename(d) for d in db_list])}")
        if args.dry_run:
            print(f"模式: 測試模式（不更新數據庫）")
        print(f"預計時間: 約 {len(video_list) * (GEMINI_DELAY + YOUTUBE_DELAY + 2) / 60:.1f} 分鐘")
        print(f"{'='*80}")

        # 處理每個視頻
        success = 0
        failed = 0
        results = {}

        for idx, (video_id, video_uuid) in enumerate(video_list, 1):
            print(f"\n[{idx}/{len(video_list)}]", end="")

            sentiment = analyze_video_comments(video_id, video_uuid, youtube, gemini)

            if sentiment is None and idx == 1:
                # 第一個視頻就失敗，可能是 API 問題
                print("\n\n❌ 分析失敗！請檢查 API 配置和配額。")
                return 1

            # 注意: sentiment 可能是 0.0 (有效值)，也可能是 None (失敗)
            if sentiment is not None:
                results[video_id] = sentiment
                success += 1

                # 更新數據庫
                if not args.dry_run:
                    for db in db_list:
                        updated = update_comment_sentiment(db, video_id, sentiment)
                        if updated > 0:
                            print(f"  更新 {os.path.basename(db)}: {updated} 條記錄")
                else:
                    print(f"  [測試模式] 將更新所有數據庫")
            else:
                failed += 1
                print(f"  ⚠️  跳過此視頻")

        # 顯示摘要
        print(f"\n\n{'='*80}")
        print(f"批次分析完成")
        print(f"{'='*80}")
        print(f"處理: {len(video_list)} 個視頻")
        print(f"成功: {success}")
        print(f"失敗: {failed}")

        if success > 0 and not args.dry_run:
            print(f"\n✓ 已更新所有數據庫的 comment_sentiment 字段")

            # 顯示更新後的統計
            print(f"\n最新狀態:")
            for db in db_list:
                stats = get_database_stats(db)
                if stats:
                    print(f"  {os.path.basename(db)}:")
                    print(f"    待分析: {stats['pending']}")
                    print(f"    已分析: {stats['analyzed']}")

        print(f"{'='*80}\n")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷")
        print("💡 提示: 使用 --resume 參數可以繼續未完成的分析")
        return 1

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
