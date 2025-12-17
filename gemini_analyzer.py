#!/usr/bin/env python3
"""
Gemini Video Analyzer - 使用 Vertex AI Gemini API 分析 YouTube 影片
"""

import os
import json
import time
import argparse
from typing import Optional, Dict, List
from dotenv import load_dotenv
from google import genai
from google.genai.types import Part, GenerateContentConfig
from db_manager import DatabaseManager

# 載入環境變數
load_dotenv()

# 定義分析 prompt - 針對 Youtuber_Financial_Data 表的 23 個欄位
ANALYSIS_PROMPT = """
請仔細分析這個 YouTube 財經影片，並以 JSON 格式輸出以下欄位。請確保回傳的是有效的 JSON 格式，不要包含任何其他文字或說明。

請分析影片內容並返回以下 JSON 結構（請只回傳 JSON，不要有其他文字）：

{
  "stock_ticker": "影片主要討論的股票代碼（例如 AAPL, TSLA, NVDA），如果沒有明確提及則為 null",
  "text_type": 1,
  "video_sentiment": 0.5,
  "financial_ratio": 0.5,
  "celebrity": 0,
  "relevancy": 0.5,
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

欄位說明：
1. stock_ticker (TEXT): 股票代碼，例如 "AAPL", "TSLA"
2. text_type (INTEGER): 1 = 功能導向（分析、數據、事實）, 0 = 社會聯繫導向（意見、觀點）
3. video_sentiment (REAL): 影片整體情感 -1（極度負面）到 1（極度正面）
4. financial_ratio (REAL): 財務相關元素比例 0 到 1
5. celebrity (INTEGER): 1 = 提及名人或知名投資者, 0 = 沒有
6. relevancy (REAL): 核心訊息相關性 0 到 1
7. long_term_competitiveness (INTEGER): 1 = 強調長期競爭力, 0 = 沒有
8. short_term_focus (INTEGER): 1 = 專注短期市場, 0 = 沒有
9. ceo_leadership_style (INTEGER): 1 = 提及 CEO 管理風格, 0 = 沒有
10. earnings_expectation_gap (REAL): 收益預期差距 -1（遠低於預期）到 1（遠高於預期）
11. stock_price_growth_trend (REAL): 股價趨勢 -1（下跌）到 1（上漲）
12. market_demand (REAL): 市場需求 -1（低）到 1（高）
13. market_capitalization (INTEGER): 1 = 提及市值, 0 = 沒有
14. target_price (INTEGER): 1 = 提及目標價, 0 = 沒有
15. financial_health (REAL): 財務健康度 -1（差）到 1（優）
16. valuation (REAL): 估值評估 -1（高估）到 1（低估）
17. policy_impact (REAL): 政策影響 -1（負面）到 1（正面）

請根據影片內容客觀評估這些指標。如果某個指標在影片中沒有明確提及，請使用 0 或 0.0 作為中性值。
只輸出 JSON，不要包含任何其他說明文字。
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

    def analyze_video(self, youtube_url: str, max_retries: int = 3) -> Optional[Dict]:
        """
        分析單一 YouTube 影片

        Args:
            youtube_url: YouTube 影片網址
            max_retries: 最大重試次數

        Returns:
            分析結果的字典，失敗則返回 None
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
                result['raw_json'] = response_text

                print(f"  ✓ 成功分析影片")
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
                    return None

            except Exception as e:
                print(f"  ✗ 分析失敗: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  等待 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
                else:
                    print(f"  已達最大重試次數，放棄此影片")
                    return None

        return None

    def save_analysis_to_db(self, video_id: str, analysis: Dict, db: DatabaseManager) -> bool:
        """
        將分析結果儲存到資料庫

        Args:
            video_id: YouTube 影片 ID
            analysis: 分析結果字典
            db: 資料庫管理器實例

        Returns:
            是否儲存成功
        """
        try:
            # 從資料庫取得影片的資訊
            db.cursor.execute(
                "SELECT like_count, comment_count, view_count, published_at FROM videos WHERE video_id = ?",
                (video_id,)
            )
            video_data = db.cursor.fetchone()

            if not video_data:
                print(f"  ✗ 找不到影片 {video_id} 在資料庫中")
                return False

            # 準備插入資料
            financial_data = {
                'video_id': video_id,
                'stock_ticker': analysis.get('stock_ticker'),
                'like_number': video_data['like_count'],
                'comment_number': video_data['comment_count'],
                'view_number': video_data['view_count'],
                'published_time': video_data['published_at'],
                'text_type': analysis.get('text_type', 0),
                'video_sentiment': analysis.get('video_sentiment', 0.0),
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
                'raw_json': analysis.get('raw_json', json.dumps(analysis))
            }

            # 插入資料庫
            db.cursor.execute("""
                INSERT OR IGNORE INTO Youtuber_Financial_Data (
                    video_id, stock_ticker, like_number, comment_number,
                    view_number, published_time,
                    text_type, video_sentiment, financial_ratio, celebrity,
                    relevancy, long_term_competitiveness, short_term_focus,
                    ceo_leadership_style, earnings_expectation_gap,
                    stock_price_growth_trend, market_demand, market_capitalization,
                    target_price, financial_health, valuation, policy_impact, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                financial_data['video_id'],
                financial_data['stock_ticker'],
                financial_data['like_number'],
                financial_data['comment_number'],
                financial_data['view_number'],
                financial_data['published_time'],
                financial_data['text_type'],
                financial_data['video_sentiment'],
                financial_data['financial_ratio'],
                financial_data['celebrity'],
                financial_data['relevancy'],
                financial_data['long_term_competitiveness'],
                financial_data['short_term_focus'],
                financial_data['ceo_leadership_style'],
                financial_data['earnings_expectation_gap'],
                financial_data['stock_price_growth_trend'],
                financial_data['market_demand'],
                financial_data['market_capitalization'],
                financial_data['target_price'],
                financial_data['financial_health'],
                financial_data['valuation'],
                financial_data['policy_impact'],
                financial_data['raw_json']
            ))

            db.conn.commit()
            print(f"  ✓ 分析結果已儲存到資料庫")
            return True

        except Exception as e:
            print(f"  ✗ 儲存到資料庫失敗: {e}")
            return False


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

    # 檢查是否已分析過
    db.cursor.execute(
        "SELECT id FROM Youtuber_Financial_Data WHERE video_id = ?",
        (video_id,)
    )
    if db.cursor.fetchone():
        print(f"\n⚠ 此影片已分析過，跳過")
        return

    # 分析影片
    analysis = analyzer.analyze_video(video['url'])

    if analysis:
        # 儲存結果
        analyzer.save_analysis_to_db(video_id, analysis, db)
        print(f"\n✓ 分析完成")
    else:
        print(f"\n✗ 分析失敗")


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
        analysis = analyzer.analyze_video(video['url'])

        if analysis:
            # 儲存結果
            if analyzer.save_analysis_to_db(video['video_id'], analysis, db):
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
