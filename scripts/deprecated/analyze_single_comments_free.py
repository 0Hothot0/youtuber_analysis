#!/usr/bin/env python3
"""
使用 Gemini API Key 的留言情緒分析器（免費版本）
不需要 Google Cloud 計費
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
from dotenv import load_dotenv

# 嘗試導入新的 google.genai 套件
try:
    from google import genai
    USE_NEW_API = True
except ImportError:
    import google.generativeai as genai
    USE_NEW_API = False

load_dotenv()

# API 延遲設定（秒）
GEMINI_DELAY = 10
YOUTUBE_DELAY = 0.5

# 進度檔案
PROGRESS_FILE = ".comment_analysis_progress.json"

# Gemini 留言情緒分析提示詞
COMMENT_SENTIMENT_PROMPT = """分析以下 YouTube 影片留言的整體情緒。

請給出一個 -1 到 1 之間的數值：
- 1.0 = 非常正面（極度看好、強烈推薦、高度讚賞）
- 0.5 = 正面（看好、認同、喜歡）
- 0.0 = 中性（中立、客觀、無明顯傾向）
- -0.5 = 負面（不看好、質疑、批評）
- -1.0 = 非常負面（強烈反對、嚴重批評、極度不滿）

分析考慮因素：
1. 整體語氣（正面、中性、負面）
2. 情緒強度（溫和、適中、強烈）
3. 支持/反對的比例
4. 用詞選擇（讚美、客觀、批評）

只需回傳數字，不要任何其他文字。

留言內容：
"""


class GeminiAPIAnalyzer:
    """使用 Gemini API Key 的分析器"""

    def __init__(self, api_key: str, model: str = "models/gemini-2.5-flash"):
        """
        初始化 Gemini API 分析器

        Args:
            api_key: Gemini API Key
            model: 使用的模型
        """
        self.api_key = api_key
        self.model = model

        if USE_NEW_API:
            # 使用新的 google.genai API
            self.client = genai.Client(api_key=api_key)
        else:
            # 使用舊的 google.generativeai API
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)

        print(f"✓ 成功初始化 Gemini API (模型: {model}, API: {'新版' if USE_NEW_API else '舊版'})")

    def analyze_comment_sentiment(self, comments_text: str, max_retries: int = 3) -> Optional[float]:
        """
        分析留言情緒

        Args:
            comments_text: 合併的留言文字
            max_retries: 最大重試次數

        Returns:
            float: 情緒分數 (-1 到 1)，或 None（分析失敗）
        """
        if not comments_text or not comments_text.strip():
            return 0.0

        # 截斷過長的留言
        max_chars = 30000
        if len(comments_text) > max_chars:
            comments_text = comments_text[:max_chars]
            print(f"      ⚠ 留言過長，截斷至 {max_chars} 字元")

        for attempt in range(max_retries):
            try:
                full_prompt = COMMENT_SENTIMENT_PROMPT + "\n" + comments_text

                if USE_NEW_API:
                    # 使用新的 API
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=full_prompt,
                        config={
                            'temperature': 0.1,
                            'max_output_tokens': 50  # 增加到 50 避免截斷
                        }
                    )
                    # 從回應中提取文字
                    if hasattr(response, 'text') and response.text and response.text != 'None':
                        sentiment_text = response.text.strip()
                    elif hasattr(response, 'candidates') and response.candidates:
                        # 從 candidates 中提取
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content:
                            content = candidate.content
                            if hasattr(content, 'parts') and content.parts:
                                sentiment_text = content.parts[0].text.strip()
                            else:
                                print(f"      ⚠ Content 沒有 parts")
                                if attempt < max_retries - 1:
                                    time.sleep(2 ** attempt)
                                continue
                        else:
                            print(f"      ⚠ Candidate 沒有 content")
                            if attempt < max_retries - 1:
                                time.sleep(2 ** attempt)
                            continue
                    else:
                        print(f"      ⚠ 無法從回應中提取文字")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                        continue
                else:
                    # 使用舊的 API
                    response = self.client.generate_content(
                        full_prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=50
                        )
                    )
                    sentiment_text = response.text.strip()

                # 解析回應
                sentiment = float(sentiment_text)

                # 驗證範圍
                if -1.0 <= sentiment <= 1.0:
                    return sentiment
                else:
                    print(f"      ⚠ 情緒分數超出範圍: {sentiment}")
                    return None

            except ValueError as e:
                print(f"      ✗ 無法解析情緒分數: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue

            except Exception as e:
                print(f"      ✗ API 錯誤 (嘗試 {attempt + 1}/{max_retries}): {str(e)[:100]}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue

        return None


class CommentAnalyzer:
    """留言情緒分析器"""

    def __init__(self, youtube: YouTubeSearcher, gemini: GeminiAPIAnalyzer, dry_run: bool = False):
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
            print(f"      ✗ YouTube API 錯誤: {str(e)[:100]}")
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
            print(f"      ✗ Gemini API 錯誤: {str(e)[:100]}")
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
        description="使用 Gemini API Key 的留言情緒分析（免費版本）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 分析 joseph 資料庫（2年期）
  python3 scripts/analyze_single_comments_free.py --db joseph_2years

  # 分析所有 single 資料庫
  python3 scripts/analyze_single_comments_free.py --db all

  # 測試模式
  python3 scripts/analyze_single_comments_free.py --db joseph_2years --dry-run --limit 3
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
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not youtube_api_key:
        print("❌ 錯誤：未設定 YOUTUBE_API_KEY")
        return 1

    if not gemini_api_key:
        print("❌ 錯誤：未設定 GEMINI_API_KEY")
        print("提示：請在 .env 檔案中加入 GEMINI_API_KEY")
        return 1

    try:
        # 初始化客戶端
        print("\n" + "="*80)
        print("Single 資料庫留言情緒分析 (Gemini API 免費版)")
        print("="*80)
        print("\n初始化 API 客戶端...")

        youtube = YouTubeSearcher(youtube_api_key)
        gemini = GeminiAPIAnalyzer(gemini_api_key, model="models/gemini-2.5-flash")

        print("✓ 所有 API 客戶端初始化成功\n")

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
                        print(f"      ✓ 更新 {updated} 筆記錄")
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
