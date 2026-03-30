#!/usr/bin/env python3
"""
以single数据库为准，分析comment_sentiment并同步到其他数据库
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

GEMINI_DELAY = 10
YOUTUBE_DELAY = 0.5


def get_unique_videos(db_path):
    """获取数据库中需要分析的唯一video_id列表"""
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
    """分析单个视频的评论情感"""
    print(f"\n  处理视频: {video_id} (UUID: {video_uuid[:8]}...)")

    # 步骤1: 抓取评论
    print(f"  抓取评论...")
    comments = youtube.get_video_comments(video_id)

    # 处理留言被关闭的情况
    if comments is None:
        print(f"  留言已关闭 - 返回 None")
        return None

    # 处理无留言的情况
    if not comments.strip():
        print(f"  无留言 - 返回 0.0")
        return 0.0

    comment_count = len(comments.split('\n'))
    print(f"  找到 {comment_count} 则留言 ({len(comments)} 字符)")

    time.sleep(YOUTUBE_DELAY)

    # 步骤2: 分析情绪
    print(f"  分析情绪...")
    sentiment = gemini.analyze_comment_sentiment(comments)

    if sentiment is None:
        print(f"  ✗ 情绪分析失败")
        return None

    print(f"  情绪分数: {sentiment:.3f}")
    time.sleep(GEMINI_DELAY)

    return sentiment


def update_comment_sentiment(db_path, video_id, sentiment):
    """更新数据库中指定video_id的所有记录的comment_sentiment"""
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


def sync_to_source_databases(video_id, sentiment, source_dbs):
    """将sentiment同步到源数据库"""
    total_updated = 0

    for db_path in source_dbs:
        if not os.path.exists(db_path):
            continue

        updated = update_comment_sentiment(db_path, video_id, sentiment)
        if updated > 0:
            print(f"    同步到 {os.path.basename(db_path)}: {updated} 条记录")
            total_updated += updated

    return total_updated


def main():
    parser = argparse.ArgumentParser(
        description="以single数据库为准分析comment_sentiment"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="限制处理视频数量（用于测试）"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="测试模式（不更新数据库）"
    )

    args = parser.parse_args()

    # 检查环境变量
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not youtube_api_key:
        print("❌ 错误：未设定 YOUTUBE_API_KEY")
        return 1

    if not project_id:
        print("❌ 错误：未设定 GOOGLE_CLOUD_PROJECT")
        return 1

    try:
        # 初始化客户端
        print("\n初始化客户端...")
        youtube = YouTubeSearcher(youtube_api_key)

        # 尝试多个区域和模型组合
        regions_to_try = [
            ("us-central1", "gemini-1.5-flash-001"),
            ("us-central1", "gemini-1.5-pro-001"),
            ("us-east4", "gemini-1.5-flash-001"),
            ("us-west1", "gemini-1.5-flash-001"),
        ]

        gemini = None
        for region, model in regions_to_try:
            try:
                print(f"尝试区域: {region}, 模型: {model}")
                test_gemini = GeminiVideoAnalyzer(
                    project_id=project_id,
                    location=region,
                    model=model
                )
                # 简单测试
                test_result = test_gemini.analyze_comment_sentiment("test comment")
                if test_result is not None:
                    gemini = test_gemini
                    print(f"✓ 成功！使用区域: {region}, 模型: {model}")
                    break
            except Exception as e:
                print(f"  ✗ 失败: {str(e)[:100]}")
                continue

        if not gemini:
            print("\n❌ 无法找到可用的Gemini配置")
            print("请检查:")
            print("1. Google Cloud项目权限")
            print("2. Vertex AI API是否启用")
            print("3. 账户是否有足够的配额")
            return 1

        # 数据库列表
        single_dbs = [
            "youtube_analysis_2years_single.db",
            "youtube_analysis_3months_single.db"
        ]

        source_dbs = [
            "youtube_analysis_2years.db",
            "youtube_analysis_3months.db"
        ]

        # 收集所有需要分析的视频
        all_videos = {}

        for db in single_dbs:
            if not os.path.exists(db):
                print(f"⚠ 数据库不存在: {db}")
                continue

            videos = get_unique_videos(db)
            print(f"\n{db}: {len(videos)} 个视频需要分析")

            for video_id, video_uuid in videos:
                if video_id not in all_videos:
                    all_videos[video_id] = video_uuid

        if not all_videos:
            print("\n✓ 所有视频都已分析完成！")
            return 0

        video_list = list(all_videos.items())

        if args.limit:
            video_list = video_list[:args.limit]

        print(f"\n{'='*80}")
        print(f"Comment Sentiment 批次分析")
        print(f"{'='*80}")
        print(f"待处理视频: {len(video_list)} 个")
        print(f"目标数据库: {', '.join([os.path.basename(d) for d in single_dbs + source_dbs])}")
        if args.dry_run:
            print(f"模式: 测试模式（不更新数据库）")
        print(f"预计时间: 约 {len(video_list) * (GEMINI_DELAY + YOUTUBE_DELAY + 2) / 60:.1f} 分钟")
        print(f"{'='*80}")

        # 处理每个视频
        success = 0
        failed = 0
        results = {}

        for idx, (video_id, video_uuid) in enumerate(video_list, 1):
            print(f"\n[{idx}/{len(video_list)}]", end="")

            sentiment = analyze_video_comments(video_id, video_uuid, youtube, gemini)

            if sentiment is None and idx == 1:
                # 第一个视频就失败，可能是API问题
                print("\n\n❌ 分析失败！请检查API配置和配额。")
                return 1

            if sentiment is not None or sentiment == 0.0:
                results[video_id] = sentiment
                success += 1

                # 更新数据库
                if not args.dry_run:
                    # 更新single数据库
                    for db in single_dbs:
                        if os.path.exists(db):
                            updated = update_comment_sentiment(db, video_id, sentiment)
                            if updated > 0:
                                print(f"  更新 {os.path.basename(db)}: {updated} 条记录")

                    # 同步到源数据库
                    synced = sync_to_source_databases(video_id, sentiment, source_dbs)
                    if synced > 0:
                        print(f"  同步到源数据库: {synced} 条记录")
                else:
                    print(f"  [测试模式] 将更新所有数据库")
            else:
                failed += 1

        # 显示摘要
        print(f"\n\n{'='*80}")
        print(f"批次分析完成")
        print(f"{'='*80}")
        print(f"处理: {len(video_list)} 个视频")
        print(f"成功: {success}")
        print(f"失败: {failed}")

        if success > 0 and not args.dry_run:
            print(f"\n✓ 已更新所有数据库的comment_sentiment字段")
            print(f"  - 2个single数据库")
            print(f"  - 2个源数据库")

        print(f"{'='*80}\n")

        return 0

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
