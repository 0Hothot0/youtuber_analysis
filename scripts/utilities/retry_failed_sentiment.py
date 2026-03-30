#!/usr/bin/env python3
"""
重試失敗的留言情緒分析
使用更嚴格的提示詞和正則表達式提取數字
"""

import os
import sys
import sqlite3
import time
import json
import re
import requests
from pathlib import Path
from typing import Optional, List, Tuple
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.youtube_search import YouTubeSearcher

load_dotenv()

# Gemini API 設定
GEMINI_API_KEY = "AIzaSyCRHKVhhIoTKeYdV7jtoms2A_sihROeXX0"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

# 延遲設定
GEMINI_DELAY = 2
YOUTUBE_DELAY = 0.5

# 更嚴格的提示詞
STRICT_PROMPT = """Analyze sentiment of these YouTube comments. Return ONLY a decimal number between -1.0 and 1.0. Nothing else.

Examples:
- Very negative: -1.0
- Negative: -0.5
- Neutral: 0.0
- Positive: 0.5
- Very positive: 1.0

Comments:
"""

# 所有 single 資料庫
DATABASES = [
    'youtube_analysis_2years_single.db',
    'youtube_analysis_3months_single.db',
    'youtube_analysis_1month_single.db',
    'youtube_analysis_6months_single.db',
    'youtube_analysis_1year_single.db',
    'youtube_analysis_2years_single_joseph.db',
    'youtube_analysis_3months_single_joseph.db',
    'youtube_analysis_1month_single_joseph.db',
    'youtube_analysis_6months_single_joseph.db',
    'youtube_analysis_1year_single_joseph.db',
]


def extract_number(text: str) -> Optional[float]:
    """從文本中提取數字（使用正則表達式）"""
    # 尋找 -1.0 到 1.0 之間的浮點數
    pattern = r'-?[01]\.?\d*'
    matches = re.findall(pattern, text)

    if matches:
        try:
            # 取第一個匹配的數字
            num = float(matches[0])
            # 確保在範圍內
            return max(-1.0, min(1.0, num))
        except:
            pass

    return None


def analyze_sentiment_strict(comments: str, api_key: str) -> Optional[float]:
    """使用嚴格提示詞分析情緒，並嘗試提取數字"""
    if not comments or not comments.strip():
        return 0.0

    # 截斷過長的留言
    max_chars = 20000
    if len(comments) > max_chars:
        comments = comments[:max_chars]

    url = f"{GEMINI_API_URL}?key={api_key}"
    headers = {"Content-Type": "application/json"}

    payload = {
        "contents": [{
            "parts": [{
                "text": STRICT_PROMPT + comments
            }]
        }],
        "generationConfig": {
            "temperature": 0.0,  # 降低隨機性
            "maxOutputTokens": 20,  # 減少 token
            "topP": 0.1,  # 更保守的生成
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        if "candidates" in result and len(result["candidates"]) > 0:
            candidate = result["candidates"][0]

            if "content" in candidate and "parts" in candidate["content"]:
                text = candidate["content"]["parts"][0]["text"].strip()

                # 嘗試直接解析
                try:
                    sentiment = float(text)
                    return max(-1.0, min(1.0, sentiment))
                except ValueError:
                    # 使用正則表達式提取
                    extracted = extract_number(text)
                    if extracted is not None:
                        return extracted

                    print(f"      無法解析: {text[:50]}")
                    return None
            else:
                return None
        else:
            return None

    except Exception as e:
        print(f"      API 錯誤: {e}")
        return None


def get_failed_videos() -> List[Tuple[str, str]]:
    """取得所有待處理的影片"""
    video_map = {}  # video_uuid -> video_id

    for db_path in DATABASES:
        if not os.path.exists(db_path):
            continue

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT video_uuid, video_id
            FROM Youtuber_Financial_Data
            WHERE comment_sentiment = 0
        """)

        for video_uuid, video_id in cursor.fetchall():
            if video_uuid not in video_map:
                video_map[video_uuid] = video_id

        conn.close()

    return list(video_map.items())


def update_all_databases(video_uuid: str, sentiment: Optional[float]) -> int:
    """更新所有資料庫中的 comment_sentiment"""
    total_updated = 0

    for db_path in DATABASES:
        if not os.path.exists(db_path):
            continue

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE Youtuber_Financial_Data
            SET comment_sentiment = ?
            WHERE video_uuid = ?
        """, (sentiment, video_uuid))

        updated = cursor.rowcount
        total_updated += updated

        conn.commit()
        conn.close()

    return total_updated


def main():
    print("="*80)
    print("重試失敗的留言情緒分析")
    print("="*80)

    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    if not youtube_api_key:
        print("❌ 錯誤：請在 .env 中設定 YOUTUBE_API_KEY")
        return 1

    print(f"\nGemini API Key: {GEMINI_API_KEY[:20]}...")
    print(f"YouTube API Key: {youtube_api_key[:20]}...")

    youtube = YouTubeSearcher(youtube_api_key)

    # 取得待處理影片
    print(f"\n取得待處理影片清單...")
    videos = get_failed_videos()

    print(f"\n{'='*80}")
    print(f"待處理影片: {len(videos)} 部")
    print(f"{'='*80}")

    if len(videos) == 0:
        print(f"\n✓ 所有影片已分析完成")
        return 0

    success = 0
    failed = 0
    no_comments = 0

    for idx, (video_uuid, video_id) in enumerate(videos, 1):
        print(f"\n[{idx}/{len(videos)}] 影片 {video_id}")
        print(f"  UUID: {video_uuid[:8]}...")

        try:
            # 抓取留言
            print(f"  抓取留言...")
            comments = youtube.get_video_comments(video_id)
            time.sleep(YOUTUBE_DELAY)

            # 處理留言被關閉
            if comments is None:
                print(f"  留言已關閉 - 設為 NULL")
                updated = update_all_databases(video_uuid, None)
                print(f"  更新 {updated} 筆記錄")
                no_comments += 1
                continue

            # 處理無留言
            if not comments.strip():
                print(f"  無留言 - 設為 0.0")
                updated = update_all_databases(video_uuid, 0.0)
                print(f"  更新 {updated} 筆記錄")
                no_comments += 1
                continue

            comment_count = len(comments.split('\n'))
            print(f"  找到 {comment_count} 則留言")

            # 分析情緒（使用嚴格提示詞）
            print(f"  分析情緒（嚴格模式）...")
            sentiment = analyze_sentiment_strict(comments, GEMINI_API_KEY)
            time.sleep(GEMINI_DELAY)

            if sentiment is None:
                # 最後手段：設為中性
                print(f"  ⚠ 無法分析，設為中性 (0.0)")
                sentiment = 0.0

            print(f"  ✓ 情緒分數: {sentiment:.3f}")

            # 更新所有資料庫
            updated = update_all_databases(video_uuid, sentiment)
            print(f"  更新 {updated} 筆記錄")

            success += 1

        except Exception as e:
            print(f"  ✗ 處理失敗: {e}")
            # 設為中性作為後備
            update_all_databases(video_uuid, 0.0)
            failed += 1

    # 顯示統計
    print(f"\n{'='*80}")
    print(f"重試完成")
    print(f"{'='*80}")
    print(f"處理影片: {len(videos)} 部")
    print(f"成功: {success}")
    print(f"失敗（設為中性）: {failed}")
    print(f"無留言: {no_comments}")
    print(f"{'='*80}\n")

    # 最終狀態
    print("="*80)
    print("最終狀態")
    print("="*80)

    for db_path in DATABASES:
        if not os.path.exists(db_path):
            continue

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data WHERE comment_sentiment != 0")
        analyzed = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data WHERE comment_sentiment = 0")
        pending = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data")
        total = cursor.fetchone()[0]

        conn.close()

        completion = (analyzed / total * 100) if total > 0 else 0
        print(f"{db_path:50s} : {analyzed}/{total} ({completion:.1f}%)")

    print("="*80 + "\n")


if __name__ == "__main__":
    main()
