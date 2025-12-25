#!/usr/bin/env python3
"""
Gemini Video Analyzer - 使用 Vertex AI Gemini API 分析 YouTube 影片
"""

import os
import json
import time
import argparse
import uuid
from typing import Optional, Dict, List
from dotenv import load_dotenv
from google import genai
from google.genai.types import Part, GenerateContentConfig
from db_manager import DatabaseManager

# 載入環境變數
load_dotenv()

# 定義分析 prompt - 支援多股票分析
ANALYSIS_PROMPT = """
Analyze this YouTube financial video and identify ALL PRIMARY stocks discussed.

PRIMARY stocks are those that meet at least one condition:
- The host spends significant time discussing it
- The video includes analysis, data, charts, earnings, or price commentary about it
- The stock is part of the main topic or title of the video

IGNORE casually mentioned stocks (brief mentions, comparisons, examples without analysis).

Return a JSON array. For EACH primary stock, provide one complete entry.
If NO primary stocks are found, return: []

Return ONLY valid JSON, no other text:

[
  {
    "stock_ticker": "SYMBOL",
    "text_type": 0,
    "video_sentiment": 0.0,
    "financial_ratio": 0.0,
    "celebrity": 0,
    "relevancy": 0.0,
    "long_term_competitiveness": 0,
    "short_term_focus": 0,
    "ceo_leadership_style": 0,
    "earnings_expectation_gap": 0.0,
    "stock_price_growth_trend": 0.0,
    "market_demand": 0.0,
    "market_capitalization": 0,
    "target_price": 0,
    "financial_health": 0.0,
    "valuation": 0.0,
    "policy_impact": 0.0
  }
]

Field definitions:
1. stock_ticker (TEXT): Stock symbol (e.g., "AAPL", "TSLA", "NVDA"). Required.
2. text_type (INTEGER): 1=functional (analysis/data/facts), 0=social-bond (opinion/views)
3. video_sentiment (REAL): -1 (very negative) to 1 (very positive), 0=neutral/no mention
4. financial_ratio (REAL): 0 to 1, proportion of financial elements (charts, numbers, terms)
5. celebrity (INTEGER): 1=mentions famous investors/CEOs, 0=none
6. relevancy (REAL): 0 to 1, relevance between video content and core stock message
7. long_term_competitiveness (INTEGER): 1=discusses long-term growth/industry trends, 0=no
8. short_term_focus (INTEGER): 1=focuses on recent news/short-term catalysts, 0=no
9. ceo_leadership_style (INTEGER): 1=mentions CEO management style/vision, 0=no
10. earnings_expectation_gap (REAL): -1 to 1, -1=below expectations, 0=neutral, 1=above
11. stock_price_growth_trend (REAL): -1 to 1, -1=declining, 0=neutral, 1=growing
12. market_demand (REAL): -1 to 1, -1=weak demand, 0=neutral, 1=strong demand
13. market_capitalization (INTEGER): 1=mentions market cap, 0=no
14. target_price (INTEGER): 1=mentions analyst price target, 0=no
15. financial_health (REAL): -1 to 1, -1=weak, 0=neutral, 1=strong
16. valuation (REAL): -1 to 1, -1=overvalued, 0=fairly priced, 1=undervalued
17. policy_impact (REAL): -1 to 1, -1=negative policy impact, 0=neutral, 1=positive

CRITICAL: If a metric is not mentioned in the video, use 0 or 0.0. Do NOT infer or assume values.
"""

COMMENT_SENTIMENT_PROMPT = """
Analyze the overall sentiment of the following YouTube video comments about financial/stock content.

Return ONLY a single floating-point number between -1 and 1:
- -1.0 = Very negative sentiment
- 0.0 = Neutral or mixed sentiment
- 1.0 = Very positive sentiment

IMPORTANT: Return ONLY the number, no other text. Example: 0.35

Comments to analyze:
"""


class GeminiVideoAnalyzer:
    """使用 Vertex AI Gemini API 分析 YouTube 影片"""

    def __init__(self, project_id: str, location: str = "us-central1", model: str = "gemini-2.0-flash-exp"):
        """
        初始化 Gemini 分析器

        Args:
            project_id: Google Cloud 專案 ID
            location: 區域（預設 us-central1）
            model: 使用的模型（預設 gemini-2.0-flash-exp）
        """
        self.project_id = project_id
        self.location = location
        self.model = model

        # 初始化 Gemini 客戶端
        try:
            self.client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location
            )
            print(f"✓ 成功初始化 Gemini 客戶端 (專案: {project_id}, 區域: {location})")
        except Exception as e:
            print(f"✗ 初始化 Gemini 客戶端失敗: {e}")
            raise

    def analyze_video(self, youtube_url: str, max_retries: int = 3) -> List[Dict]:
        """
        分析單一 YouTube 影片

        Args:
            youtube_url: YouTube 影片網址
            max_retries: 最大重試次數

        Returns:
            分析結果的列表（每個股票一個 dict），失敗則返回空列表
        """
        print(f"\n分析影片: {youtube_url}")

        for attempt in range(max_retries):
            try:
                # 構建請求內容
                contents = [
                    Part.from_uri(
                        file_uri=youtube_url,
                        mime_type="video/*"
                    ),
                    ANALYSIS_PROMPT
                ]

                # 呼叫 Gemini API
                print(f"  正在呼叫 Gemini API (嘗試 {attempt + 1}/{max_retries})...")
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=GenerateContentConfig(
                        temperature=0.2,  # 低溫度以獲得更一致的結果
                        max_output_tokens=2048
                    )
                )

                # 解析回應
                response_text = response.text.strip()
                print(f"  收到回應，長度: {len(response_text)} 字元")

                # 嘗試解析 JSON
                # 移除可能的 markdown 代碼塊標記
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

                result = json.loads(response_text)

                # Handle both array and single object responses
                if isinstance(result, dict):
                    result = [result]  # Wrap single object in array for backward compatibility

                # Validate it's a list
                if not isinstance(result, list):
                    print(f"  ✗ 無效的回應格式：應該是陣列，但收到 {type(result)}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"  等待 {wait_time} 秒後重試...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  已達最大重試次數，放棄此影片")
                        return []

                # Add raw_json to each result
                raw_json_str = json.dumps(result, ensure_ascii=False)
                for item in result:
                    item['raw_json'] = raw_json_str

                print(f"  ✓ 成功分析影片，找到 {len(result)} 個主要股票")
                return result

            except json.JSONDecodeError as e:
                print(f"  ✗ JSON 解析失敗: {e}")
                print(f"  原始回應: {response_text[:200]}...")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  等待 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
                else:
                    print(f"  已達最大重試次數，放棄此影片")
                    return []

            except Exception as e:
                print(f"  ✗ 分析失敗: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  等待 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
                else:
                    print(f"  已達最大重試次數，放棄此影片")
                    return []

        return []

    def save_analysis_to_db(self, video_id: str, analyses: List[Dict], db: DatabaseManager) -> int:
        """
        將分析結果儲存到資料庫

        Args:
            video_id: YouTube 影片 ID
            analyses: 分析結果列表（每個股票一個字典）
            db: 資料庫管理器實例

        Returns:
            成功儲存的記錄數量
        """
        if not analyses:
            print(f"  ⚠ 影片 {video_id} 沒有找到主要股票")
            return 0

        try:
            # 為此影片生成一個 UUID（所有股票共用）
            video_uuid = str(uuid.uuid4())

            # 從資料庫取得影片的資訊
            db.cursor.execute(
                "SELECT like_count, comment_count, view_count, published_at FROM videos WHERE video_id = ?",
                (video_id,)
            )
            video_data = db.cursor.fetchone()

            if not video_data:
                print(f"  ✗ 找不到影片 {video_id} 在資料庫中")
                return 0

            success_count = 0

            for analysis in analyses:
                stock_ticker = analysis.get('stock_ticker')
                if not stock_ticker:
                    print(f"    ⚠ 跳過無股票代碼的記錄")
                    continue

                # 準備插入資料
                financial_data = {
                    'video_uuid': video_uuid,
                    'video_id': video_id,
                    'stock_ticker': stock_ticker,
                    'like_number': video_data['like_count'],
                    'comment_number': video_data['comment_count'],
                    'view_number': video_data['view_count'],
                    'published_time': video_data['published_at'],
                    'text_type': analysis.get('text_type', 0),
                    'video_sentiment': analysis.get('video_sentiment', 0.0),
                    'comment_sentiment': 0,  # 固定為 0，無法分析留言
                    'financial_ratio': analysis.get('financial_ratio', 0.0),
                    'celebrity': analysis.get('celebrity', 0),
                    'relevancy': analysis.get('relevancy', 0.0),
                    'long_term_competitiveness': analysis.get('long_term_competitiveness', 0),
                    'short_term_focus': analysis.get('short_term_focus', 0),
                    'ceo_leadership_style': analysis.get('ceo_leadership_style', 0),
                    'earnings_expectation_gap': analysis.get('earnings_expectation_gap', 0.0),
                    'stock_price_growth_trend': analysis.get('stock_price_growth_trend', 0.0),
                    'market_demand': analysis.get('market_demand', 0.0),
                    'market_capitalization': analysis.get('market_capitalization', 0),
                    'target_price': analysis.get('target_price', 0),
                    'financial_health': analysis.get('financial_health', 0.0),
                    'valuation': analysis.get('valuation', 0.0),
                    'policy_impact': analysis.get('policy_impact', 0.0),
                    'raw_json': analysis.get('raw_json', json.dumps(analysis, ensure_ascii=False))
                }

                try:
                    # 使用 db_manager 的方法插入
                    result = db.insert_financial_data(financial_data)
                    if result:
                        success_count += 1
                        print(f"    ✓ 已儲存: {stock_ticker}")
                    else:
                        print(f"    ⚠ 略過（已存在）: {stock_ticker}")
                except Exception as e:
                    print(f"    ✗ 插入 {stock_ticker} 失敗: {e}")

            print(f"  ✓ 成功儲存 {success_count}/{len(analyses)} 個股票分析")
            return success_count

        except Exception as e:
            print(f"  ✗ 儲存到資料庫失敗: {e}")
            return 0

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
            return 0.0  # 無留言 = 中性

        # 截斷過長的留言（避免超出 token 限制）
        max_chars = 30000
        if len(comments_text) > max_chars:
            comments_text = comments_text[:max_chars]
            print(f"  ⚠ 留言過長，截斷至 {max_chars} 字元")

        for attempt in range(max_retries):
            try:
                full_prompt = COMMENT_SENTIMENT_PROMPT + "\n" + comments_text

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[full_prompt],
                    config=GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=10
                    )
                )

                # 解析回應（只取數字）
                response_text = response.text.strip()
                cleaned = ''.join(c for c in response_text if c in '-0123456789.')
                sentiment_score = float(cleaned)

                # 限制範圍
                return max(-1.0, min(1.0, sentiment_score))

            except Exception as e:
                print(f"  ✗ 情緒分析失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  等待 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
                else:
                    return None

        return None


def analyze_single_video(analyzer: GeminiVideoAnalyzer, video_id: str, db: DatabaseManager):
    """分析單一影片"""
    print(f"\n{'='*80}")
    print(f"單一影片分析")
    print(f"{'='*80}")

    # 從資料庫取得影片資訊
    db.cursor.execute("SELECT video_id, url, title FROM videos WHERE video_id = ?", (video_id,))
    video = db.cursor.fetchone()

    if not video:
        print(f"✗ 找不到影片 ID: {video_id}")
        return

    print(f"\n影片資訊:")
    print(f"  ID: {video['video_id']}")
    print(f"  標題: {video['title']}")
    print(f"  URL: {video['url']}")

    # 檢查是否已分析過（只要有任何記錄就算已分析）
    db.cursor.execute(
        "SELECT COUNT(*) FROM Youtuber_Financial_Data WHERE video_id = ?",
        (video_id,)
    )
    count = db.cursor.fetchone()[0]
    if count > 0:
        print(f"\n⚠ 此影片已分析過（有 {count} 筆記錄），跳過")
        return

    # 分析影片
    analyses = analyzer.analyze_video(video['url'])

    if analyses:
        # 儲存結果
        saved_count = analyzer.save_analysis_to_db(video_id, analyses, db)
        print(f"\n✓ 分析完成，儲存 {saved_count} 個股票")
    else:
        print(f"\n✗ 分析失敗或未找到主要股票")


def analyze_batch(analyzer: GeminiVideoAnalyzer, db: DatabaseManager,
                  limit: int = 10, youtuber_name: Optional[str] = None):
    """批次分析影片"""
    print(f"\n{'='*80}")
    print(f"批次影片分析")
    print(f"{'='*80}")

    # 構建查詢
    if youtuber_name:
        # 取得 YouTuber ID
        db.cursor.execute(
            "SELECT id FROM youtubers WHERE name LIKE ?",
            (f"%{youtuber_name}%",)
        )
        youtuber = db.cursor.fetchone()
        if not youtuber:
            print(f"✗ 找不到 YouTuber: {youtuber_name}")
            return

        # 查詢該 YouTuber 尚未分析的影片
        db.cursor.execute("""
            SELECT v.video_id, v.url, v.title
            FROM videos v
            LEFT JOIN Youtuber_Financial_Data f ON v.video_id = f.video_id
            WHERE v.youtuber_id = ? AND f.id IS NULL
            ORDER BY v.created_at DESC
            LIMIT ?
        """, (youtuber['id'], limit))
        print(f"\n分析 YouTuber: {youtuber_name}")
    else:
        # 查詢所有尚未分析的影片
        db.cursor.execute("""
            SELECT v.video_id, v.url, v.title
            FROM videos v
            LEFT JOIN Youtuber_Financial_Data f ON v.video_id = f.video_id
            WHERE f.id IS NULL
            ORDER BY v.created_at DESC
            LIMIT ?
        """, (limit,))
        print(f"\n分析所有未處理的影片")

    videos = db.cursor.fetchall()

    if not videos:
        print(f"\n✓ 沒有需要分析的影片")
        return

    print(f"找到 {len(videos)} 個影片待分析")
    print(f"{'='*80}\n")

    # 逐一分析
    success_count = 0
    fail_count = 0

    for idx, video in enumerate(videos, 1):
        print(f"\n[{idx}/{len(videos)}] 分析影片: {video['title'][:60]}...")
        print(f"  Video ID: {video['video_id']}")

        # 分析影片
        analyses = analyzer.analyze_video(video['url'])

        if analyses:
            # 儲存結果
            saved_count = analyzer.save_analysis_to_db(video['video_id'], analyses, db)
            if saved_count > 0:
                success_count += 1
            else:
                fail_count += 1
        else:
            fail_count += 1

        # 避免 API 限制，每次請求間隔 2 秒
        if idx < len(videos):
            print(f"  等待 2 秒...")
            time.sleep(2)

    # 顯示統計
    print(f"\n{'='*80}")
    print(f"批次分析完成")
    print(f"{'='*80}")
    print(f"  成功: {success_count} 個")
    print(f"  失敗: {fail_count} 個")
    print(f"  總計: {len(videos)} 個")
    print(f"{'='*80}\n")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="使用 Vertex AI Gemini 分析 YouTube 影片的財經內容"
    )

    parser.add_argument(
        "--video-id",
        help="分析指定的影片 ID"
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="批次分析未處理的影片"
    )

    parser.add_argument(
        "--youtuber",
        help="批次分析時，指定特定 YouTuber 的影片"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="批次分析的數量限制（預設 10）"
    )

    parser.add_argument(
        "--model",
        default="gemini-2.0-flash-exp",
        help="使用的 Gemini 模型（預設 gemini-2.0-flash-exp）"
    )

    args = parser.parse_args()

    # 檢查參數
    if not args.video_id and not args.batch:
        parser.print_help()
        return

    # 載入環境變數
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project_id:
        print("✗ 錯誤: 請在 .env 檔案中設定 GOOGLE_CLOUD_PROJECT")
        return

    # 初始化
    try:
        analyzer = GeminiVideoAnalyzer(
            project_id=project_id,
            location=location,
            model=args.model
        )

        db = DatabaseManager()
        db.connect()

        # 執行分析
        if args.video_id:
            analyze_single_video(analyzer, args.video_id, db)
        elif args.batch:
            analyze_batch(analyzer, db, args.limit, args.youtuber)

        db.close()

    except Exception as e:
        print(f"\n✗ 執行失敗: {e}")
        raise


if __name__ == '__main__':
    main()
