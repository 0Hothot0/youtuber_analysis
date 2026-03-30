#!/usr/bin/env python3
"""
使用 Gemini REST API 直接调用分析 comment sentiment
"""

import os
import sys
import time
import sqlite3
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.youtube_search import YouTubeSearcher

load_dotenv()

YOUTUBE_DELAY = 0.5
GEMINI_DELAY = 2

# Gemini REST API endpoint - 使用 gemini-flash-latest（配额充足）
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"


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


def analyze_comment_sentiment_rest(comments_text, api_key):
    """使用 Gemini REST API 分析评论情感"""
    if not comments_text or not comments_text.strip():
        return 0.0

    # 截断过长的留言
    max_chars = 30000
    if len(comments_text) > max_chars:
        comments_text = comments_text[:max_chars]
        print(f"  ⚠ 留言过长，截断至 {max_chars} 字符")

    prompt = f"""分析以下 YouTube 留言的整體情緒傾向。

留言內容：
{comments_text}

請只返回一個 -1 到 1 之間的數字：
- 負面情緒 = -1 到 -0.3
- 中性情緒 = -0.3 到 0.3
- 正面情緒 = 0.3 到 1

只返回數字，不要其他文字。"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 50  # 增加token限制
                }
            }

            response = requests.post(
                f"{GEMINI_API_URL}?key={api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                # 调试：打印响应结构
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate:
                        if 'parts' in candidate['content']:
                            text = candidate['content']['parts'][0]['text'].strip()
                        else:
                            # 可能直接在content中
                            text = candidate['content'].get('text', '').strip()
                    else:
                        print(f"  ✗ 响应格式错误: {result}")
                        continue

                    # 解析数字
                    cleaned = ''.join(c for c in text if c in '-0123456789.')
                    if cleaned:
                        sentiment_score = float(cleaned)
                        # 限制范围
                        return max(-1.0, min(1.0, sentiment_score))
                    else:
                        print(f"  ✗ 无法从响应中提取数字: {text}")
                        continue
                else:
                    print(f"  ✗ 响应中没有candidates: {result}")
                    continue
            else:
                error_info = response.json() if response.text else response.status_code
                print(f"  ✗ API返回错误 (尝试 {attempt + 1}/{max_retries}): {error_info}")

        except Exception as e:
            print(f"  ✗ 情绪分析失败 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}")

        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            print(f"  等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)

    return None


def analyze_video_comments(video_id, video_uuid, youtube, api_key):
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
    sentiment = analyze_comment_sentiment_rest(comments, api_key)

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
    import argparse
    parser = argparse.ArgumentParser(
        description="使用 Gemini REST API 分析 comment_sentiment"
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
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not youtube_api_key:
        print("❌ 错误：未设定 YOUTUBE_API_KEY")
        return 1

    if not gemini_api_key:
        print("❌ 错误：未设定 GEMINI_API_KEY")
        return 1

    try:
        # 初始化客户端
        print("\n初始化客户端...")
        youtube = YouTubeSearcher(youtube_api_key)
        print("✓ YouTube API 客户端初始化成功")
        print("✓ Gemini REST API 配置完成")

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
        print(f"Comment Sentiment 批次分析 (Gemini REST API)")
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

        for idx, (video_id, video_uuid) in enumerate(video_list, 1):
            print(f"\n[{idx}/{len(video_list)}]", end="")

            sentiment = analyze_video_comments(video_id, video_uuid, youtube, gemini_api_key)

            if sentiment is not None or sentiment == 0.0:
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
