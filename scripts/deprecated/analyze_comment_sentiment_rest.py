#!/usr/bin/env python3
"""
使用 Gemini REST API 分析留言情緒
適用於所有 single 資料庫
"""

import os
import sys
import sqlite3
import time
import json
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
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# 延遲設定（避免 API 限制）
GEMINI_DELAY = 2  # 秒
YOUTUBE_DELAY = 0.5  # 秒

# 留言情緒分析提示詞
COMMENT_SENTIMENT_PROMPT = """Analyze the overall sentiment of the following YouTube comments about a stock/company.

Return ONLY a single number between -1 and 1:
- 1.0 = Very positive (bullish, enthusiastic, confident)
- 0.5 = Moderately positive
- 0.0 = Neutral or mixed
- -0.5 = Moderately negative
- -1.0 = Very negative (bearish, pessimistic, critical)

Comments:
"""


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
            "maxOutputTokens": 10
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


def get_video_uuids_from_db(db_path: str) -> List[Tuple[str, str]]:
    """從資料庫取得所有 video_uuid 和 video_id（去重）"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 取得唯一的 video_uuid 和 video_id（comment_sentiment = 0）
    cursor.execute("""
        SELECT DISTINCT video_uuid, video_id
        FROM Youtuber_Financial_Data
        WHERE comment_sentiment = 0
        ORDER BY video_uuid
    """)

    videos = cursor.fetchall()
    conn.close()

    return videos


def update_comment_sentiment(db_path: str, video_uuid: str, sentiment: Optional[float]) -> int:
    """更新指定 video_uuid 的所有記錄的 comment_sentiment"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Youtuber_Financial_Data
        SET comment_sentiment = ?
        WHERE video_uuid = ?
    """, (sentiment, video_uuid))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated


def process_database(db_path: str, youtube_api_key: str, gemini_api_key: str):
    """處理單一資料庫"""
    print(f"\n{'='*80}")
    print(f"處理資料庫: {db_path}")
    print(f"{'='*80}")

    if not os.path.exists(db_path):
        print(f"❌ 資料庫不存在")
        return

    # 初始化 YouTube 客戶端
    youtube = YouTubeSearcher(youtube_api_key)

    # 取得待處理的影片
    videos = get_video_uuids_from_db(db_path)
    print(f"待處理影片: {len(videos)} 部")

    if len(videos) == 0:
        print(f"✓ 所有影片已分析完成")
        return

    # 處理每部影片
    success = 0
    failed = 0
    no_comments = 0

    for idx, (video_uuid, video_id) in enumerate(videos, 1):
        print(f"\n  [{idx}/{len(videos)}] 影片 {video_id} (UUID: {video_uuid[:8]}...)")

        try:
            # 1. 抓取留言
            print(f"    抓取留言...")
            comments = youtube.get_video_comments(video_id)
            time.sleep(YOUTUBE_DELAY)

            # 處理留言被關閉
            if comments is None:
                print(f"    留言已關閉 - 設為 NULL")
                update_comment_sentiment(db_path, video_uuid, None)
                no_comments += 1
                continue

            # 處理無留言
            if not comments.strip():
                print(f"    無留言 - 設為 0.0")
                update_comment_sentiment(db_path, video_uuid, 0.0)
                no_comments += 1
                continue

            comment_count = len(comments.split('\n'))
            print(f"    找到 {comment_count} 則留言")

            # 2. 分析情緒
            print(f"    分析情緒...")
            sentiment = analyze_sentiment_with_gemini(comments, gemini_api_key)
            time.sleep(GEMINI_DELAY)

            if sentiment is None:
                print(f"    ✗ 情緒分析失敗")
                failed += 1
                continue

            print(f"    ✓ 情緒分數: {sentiment:.3f}")

            # 3. 更新資料庫
            updated = update_comment_sentiment(db_path, video_uuid, sentiment)
            print(f"    更新 {updated} 筆記錄")

            success += 1

        except Exception as e:
            print(f"    ✗ 處理失敗: {e}")
            failed += 1

    # 顯示統計
    print(f"\n{'='*80}")
    print(f"資料庫處理完成: {db_path}")
    print(f"{'='*80}")
    print(f"成功: {success}")
    print(f"失敗: {failed}")
    print(f"無留言: {no_comments}")
    print(f"{'='*80}\n")


def main():
    print("="*80)
    print("留言情緒批次分析 - 使用 Gemini REST API")
    print("="*80)

    # 檢查 YouTube API Key
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    if not youtube_api_key:
        print("❌ 錯誤：請在 .env 中設定 YOUTUBE_API_KEY")
        return 1

    # 定義所有 single 資料庫
    databases = [
        # Tom Nash
        'youtube_analysis_2years_single.db',
        'youtube_analysis_3months_single.db',
        'youtube_analysis_1month_single.db',
        'youtube_analysis_6months_single.db',
        'youtube_analysis_1year_single.db',

        # Joseph
        'youtube_analysis_2years_single_joseph.db',
        'youtube_analysis_3months_single_joseph.db',
        'youtube_analysis_1month_single_joseph.db',
        'youtube_analysis_6months_single_joseph.db',
        'youtube_analysis_1year_single_joseph.db',
    ]

    print(f"\n總共需要處理 {len(databases)} 個資料庫")
    print(f"Gemini API Key: {GEMINI_API_KEY[:20]}...")
    print(f"YouTube API Key: {youtube_api_key[:20]}...")

    # 處理每個資料庫
    for db_path in databases:
        process_database(db_path, youtube_api_key, GEMINI_API_KEY)

    print("\n" + "="*80)
    print("所有資料庫處理完成")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
