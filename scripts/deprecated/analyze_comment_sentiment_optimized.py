#!/usr/bin/env python3
"""
使用 Gemini REST API 分析留言情緒（優化版）
一次處理，更新所有相關資料庫
"""

import os
import sys
import sqlite3
import time
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Set
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.youtube_search import YouTubeSearcher

load_dotenv()

# Gemini API 設定
GEMINI_API_KEY = "AIzaSyCRHKVhhIoTKeYdV7jtoms2A_sihROeXX0"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

# 延遲設定（避免 API 限制）
GEMINI_DELAY = 2  # 秒
YOUTUBE_DELAY = 0.5  # 秒

# 留言情緒分析提示詞（簡化版）
COMMENT_SENTIMENT_PROMPT = """Rate the sentiment of these YouTube comments from -1 (very negative) to 1 (very positive). Return only the number.

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


def analyze_sentiment_with_gemini(comments: str, api_key: str) -> Optional[float]:
    """使用 Gemini REST API 分析留言情緒"""
    if not comments or not comments.strip():
        return 0.0

    # 截斷過長的留言
    max_chars = 20000
    if len(comments) > max_chars:
        comments = comments[:max_chars]
        print(f"      ⚠ 留言過長，截斷至 {max_chars} 字元")

    # 構建請求
    url = f"{GEMINI_API_URL}?key={api_key}"
    headers = {"Content-Type": "application/json"}

    payload = {
        "contents": [{
            "parts": [{
                "text": COMMENT_SENTIMENT_PROMPT + comments
            }]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 200
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()

        # 解析回應
        if "candidates" in result and len(result["candidates"]) > 0:
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()

            # 嘗試解析數字
            try:
                sentiment = float(text)
                # 限制範圍在 -1 到 1
                sentiment = max(-1.0, min(1.0, sentiment))
                return sentiment
            except ValueError:
                print(f"      ✗ 無法解析情緒分數: {text}")
                return None
        else:
            print(f"      ✗ API 回應無效")
            return None

    except requests.exceptions.RequestException as e:
        print(f"      ✗ API 請求失敗: {e}")
        return None
    except Exception as e:
        print(f"      ✗ 解析失敗: {e}")
        return None


def get_all_unique_videos() -> Dict[str, Set[str]]:
    """
    取得所有資料庫中需要處理的唯一影片
    返回: {video_uuid: {video_id}, ...}
    """
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

    return video_map


def update_all_databases(video_uuid: str, sentiment: Optional[float]) -> int:
    """在所有資料庫中更新指定 video_uuid 的 comment_sentiment"""
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
    print("留言情緒批次分析 - 使用 Gemini REST API（優化版）")
    print("="*80)

    # 檢查 YouTube API Key
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    if not youtube_api_key:
        print("❌ 錯誤：請在 .env 中設定 YOUTUBE_API_KEY")
        return 1

    print(f"\nGemini API Key: {GEMINI_API_KEY[:20]}...")
    print(f"YouTube API Key: {youtube_api_key[:20]}...")

    # 初始化 YouTube 客戶端
    youtube = YouTubeSearcher(youtube_api_key)

    # 取得所有唯一影片
    print(f"\n取得待處理影片清單...")
    video_map = get_all_unique_videos()

    print(f"\n{'='*80}")
    print(f"待處理唯一影片: {len(video_map)} 部")
    print(f"將同步更新所有相關資料庫")
    print(f"{'='*80}")

    if len(video_map) == 0:
        print(f"\n✓ 所有影片已分析完成")
        return 0

    # 處理每部影片
    success = 0
    failed = 0
    no_comments = 0

    videos = list(video_map.items())

    for idx, (video_uuid, video_id) in enumerate(videos, 1):
        print(f"\n[{idx}/{len(videos)}] 影片 {video_id}")
        print(f"  UUID: {video_uuid[:8]}...")

        try:
            # 1. 抓取留言
            print(f"  抓取留言...")
            comments = youtube.get_video_comments(video_id)
            time.sleep(YOUTUBE_DELAY)

            # 處理留言被關閉
            if comments is None:
                print(f"  留言已關閉 - 設為 NULL")
                updated = update_all_databases(video_uuid, None)
                print(f"  更新 {updated} 筆記錄（跨所有資料庫）")
                no_comments += 1
                continue

            # 處理無留言
            if not comments.strip():
                print(f"  無留言 - 設為 0.0")
                updated = update_all_databases(video_uuid, 0.0)
                print(f"  更新 {updated} 筆記錄（跨所有資料庫）")
                no_comments += 1
                continue

            comment_count = len(comments.split('\n'))
            print(f"  找到 {comment_count} 則留言")

            # 2. 分析情緒
            print(f"  分析情緒...")
            sentiment = analyze_sentiment_with_gemini(comments, GEMINI_API_KEY)
            time.sleep(GEMINI_DELAY)

            if sentiment is None:
                print(f"  ✗ 情緒分析失敗")
                failed += 1
                continue

            print(f"  ✓ 情緒分數: {sentiment:.3f}")

            # 3. 更新所有資料庫
            updated = update_all_databases(video_uuid, sentiment)
            print(f"  更新 {updated} 筆記錄（跨所有資料庫）")

            success += 1

        except Exception as e:
            print(f"  ✗ 處理失敗: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    # 顯示統計
    print(f"\n{'='*80}")
    print(f"批次處理完成")
    print(f"{'='*80}")
    print(f"處理影片: {len(videos)} 部")
    print(f"成功: {success}")
    print(f"失敗: {failed}")
    print(f"無留言: {no_comments}")
    print(f"{'='*80}\n")

    # 顯示每個資料庫的更新狀態
    print("="*80)
    print("各資料庫更新結果")
    print("="*80)

    for db_path in DATABASES:
        if not os.path.exists(db_path):
            print(f"{db_path:50s} : 不存在")
            continue

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data WHERE comment_sentiment != 0")
        analyzed = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data WHERE comment_sentiment = 0")
        pending = cursor.fetchone()[0]

        conn.close()

        print(f"{db_path:50s} : 已分析 {analyzed}, 待處理 {pending}")

    print("="*80 + "\n")


if __name__ == "__main__":
    main()
