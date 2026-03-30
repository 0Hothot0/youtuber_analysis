#!/usr/bin/env python3
"""
优化版：只分析高赞评论的sentiment
- 只获取点赞数最高的前10-20条评论
- 减少API消耗和token使用
- 提高情绪分析准确性
"""

import os
import sys
import time
import sqlite3
import requests
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.youtube_search import YouTubeSearcher

load_dotenv()

YOUTUBE_DELAY = 0.5
GEMINI_DELAY = 2


def get_top_liked_comments(youtube, video_id, top_n=15):
    """
    获取点赞数最高的前N条评论

    Args:
        youtube: YouTubeSearcher实例
        video_id: 视频ID
        top_n: 获取前N条高赞评论

    Returns:
        str: 高赞评论文本，或None（评论关闭）
    """
    try:
        all_comments = []
        next_page_token = None
        max_fetch = 100  # 最多获取100条评论用于排序

        while len(all_comments) < max_fetch:
            request_params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': 100,
                'textFormat': 'plainText',
                'order': 'relevance'  # 先按相关性获取
            }

            if next_page_token:
                request_params['pageToken'] = next_page_token

            response = youtube.youtube.commentThreads().list(**request_params).execute()

            for item in response.get('items', []):
                snippet = item['snippet']['topLevelComment']['snippet']
                comment_data = {
                    'text': snippet['textDisplay'],
                    'likes': snippet.get('likeCount', 0)
                }
                all_comments.append(comment_data)

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        if not all_comments:
            return ""

        # 按点赞数排序
        all_comments.sort(key=lambda x: x['likes'], reverse=True)

        # 只取前N条高赞评论
        top_comments = all_comments[:top_n]

        # 组合评论文本
        comment_texts = [c['text'] for c in top_comments]

        print(f"  获取到 {len(all_comments)} 条评论，分析前 {len(top_comments)} 条高赞评论")
        print(f"  点赞数范围: {top_comments[0]['likes']} - {top_comments[-1]['likes']}")

        return "\n".join(comment_texts)

    except Exception as e:
        error_str = str(e)
        if 'commentsDisabled' in error_str or '403' in error_str:
            return None  # 评论被关闭
        print(f"  ✗ 获取评论错误: {e}")
        return None


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
    max_chars = 10000  # 减少到10000字符（高赞评论通常更短）
    if len(comments_text) > max_chars:
        comments_text = comments_text[:max_chars]
        print(f"  ⚠ 评论过长，截断至 {max_chars} 字符")

    prompt = f"""分析以下 YouTube 高赞评论的整体情绪倾向。

这些是视频中点赞数最高的评论：
{comments_text}

请只返回一个 -1 到 1 之间的小数（保留1位小数）：
- 负面情绪（批评、失望、愤怒）: -1.0 到 -0.3
- 中性情绪（事实陈述、中立观点）: -0.2 到 0.2
- 正面情绪（赞扬、感谢、认同）: 0.3 到 1.0

只返回数字，例如：0.7 或 -0.5"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent'

            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.2,  # 稍微提高温度增加变化性
                    "maxOutputTokens": 200  # 增加到200避免被截断
                }
            }

            response = requests.post(
                f"{url}?key={api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        parts = candidate['content']['parts']
                        if len(parts) > 0 and 'text' in parts[0]:
                            text = parts[0]['text'].strip()

                            # 提取数字
                            cleaned = ''.join(c for c in text if c in '-0123456789.')
                            if cleaned:
                                sentiment_score = float(cleaned)
                                # 限制范围
                                return max(-1.0, min(1.0, sentiment_score))
                            else:
                                print(f"  ⚠ 无法从'{text}'中提取数字")

            elif response.status_code == 429:
                error = response.json()
                print(f"  ✗ API配额超限 (尝试 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return None
            else:
                print(f"  ✗ API错误 {response.status_code}")

        except Exception as e:
            print(f"  ✗ 分析失败 (尝试 {attempt + 1}/{max_retries}): {str(e)[:80]}")

        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)

    return None


def analyze_video_comments(video_id, video_uuid, youtube, api_key):
    """分析单个视频的高赞评论情感"""
    print(f"\n  处理视频: {video_id} (UUID: {video_uuid[:8]}...)")

    # 步骤1: 获取高赞评论
    print(f"  获取高赞评论...")
    comments = get_top_liked_comments(youtube, video_id, top_n=15)

    # 处理评论被关闭的情况
    if comments is None:
        print(f"  评论已关闭 - 返回 None")
        return None

    # 处理无评论的情况
    if not comments.strip():
        print(f"  无评论 - 返回 0.0")
        return 0.0

    time.sleep(YOUTUBE_DELAY)

    # 步骤2: 分析情绪
    print(f"  分析情绪...")
    sentiment = analyze_comment_sentiment_rest(comments, api_key)

    if sentiment is None:
        print(f"  ✗ 情绪分析失败")
        return None

    print(f"  ✓ 情绪分数: {sentiment:.3f}")
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
        description="使用高赞评论分析 comment_sentiment（优化版）"
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
        print("✓ 优化模式：只分析前15条高赞评论")

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
        print(f"高赞评论情绪分析 (优化版)")
        print(f"{'='*80}")
        print(f"待处理视频: {len(video_list)} 个")
        print(f"每个视频分析: 前15条高赞评论")
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
