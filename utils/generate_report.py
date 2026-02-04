#!/usr/bin/env python3
"""
生成完整的分析統計報告
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager


def generate_statistics_report():
    """生成完整的統計報告"""
    db = DatabaseManager()
    db.connect()

    print("\n" + "="*80)
    print("YouTube 影片分析統計報告")
    print(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # 1. 基本統計
    print("\n【基本統計】")
    stats = db.get_statistics()
    print(f"  YouTubers: {stats['youtubers']} 個")
    print(f"  搜尋標籤: {stats['tags']} 個")
    print(f"  總影片數: {stats['videos']} 個")
    print(f"  已分析影片: {stats['financial_data']} 個")

    if stats['videos'] > 0:
        completion_rate = (stats['financial_data'] / stats['videos']) * 100
        print(f"  完成率: {completion_rate:.1f}%")

    # 2. 按 YouTuber 統計
    print("\n【影片分布（按 YouTuber）】")
    db.cursor.execute("""
        SELECT
            COALESCE(y.name, '未指定') as youtuber,
            COUNT(v.video_id) as video_count,
            COUNT(f.id) as analyzed_count
        FROM videos v
        LEFT JOIN youtubers y ON v.youtuber_id = y.id
        LEFT JOIN Youtuber_Financial_Data f ON v.video_id = f.video_id
        GROUP BY v.youtuber_id
        ORDER BY video_count DESC
    """)

    for row in db.cursor.fetchall():
        print(f"  {row['youtuber']:25s}: {row['video_count']:3d} 個影片 (已分析: {row['analyzed_count']:3d})")

    # 3. 按搜尋關鍵字統計
    print("\n【影片分布（按搜尋關鍵字）】")
    db.cursor.execute("""
        SELECT
            search_keyword,
            COUNT(*) as count
        FROM videos
        GROUP BY search_keyword
        ORDER BY count DESC
        LIMIT 10
    """)

    for row in db.cursor.fetchall():
        print(f"  {row['search_keyword']:30s}: {row['count']:3d} 個")

    # 4. 財務指標統計（如果有分析資料）
    if stats['financial_data'] > 0:
        print("\n【財務指標統計】")

        # 4.1 股票代碼分布
        db.cursor.execute("""
            SELECT
                stock_ticker,
                COUNT(*) as count
            FROM Youtuber_Financial_Data
            WHERE stock_ticker IS NOT NULL
            GROUP BY stock_ticker
            ORDER BY count DESC
            LIMIT 10
        """)

        stock_results = db.cursor.fetchall()
        if stock_results:
            print("\n  最常提及的股票:")
            for row in stock_results:
                print(f"    {row['stock_ticker']:10s}: {row['count']:3d} 個影片")

        # 4.2 情感分析統計
        db.cursor.execute("""
            SELECT
                AVG(video_sentiment) as avg_sentiment,
                MIN(video_sentiment) as min_sentiment,
                MAX(video_sentiment) as max_sentiment
            FROM Youtuber_Financial_Data
        """)

        sentiment = db.cursor.fetchone()
        print(f"\n  影片情感分析:")
        print(f"    平均情感: {sentiment['avg_sentiment']:.3f}")
        print(f"    最負面: {sentiment['min_sentiment']:.3f}")
        print(f"    最正面: {sentiment['max_sentiment']:.3f}")

        # 4.3 財務相關度統計
        db.cursor.execute("""
            SELECT
                AVG(financial_ratio) as avg_ratio
            FROM Youtuber_Financial_Data
        """)

        ratio = db.cursor.fetchone()
        print(f"\n  財務相關度:")
        print(f"    平均: {ratio['avg_ratio']:.3f} ({ratio['avg_ratio']*100:.1f}%)")

        # 4.4 長期 vs 短期焦點
        db.cursor.execute("""
            SELECT
                SUM(long_term_competitiveness) as long_term_count,
                SUM(short_term_focus) as short_term_count
            FROM Youtuber_Financial_Data
        """)

        focus = db.cursor.fetchone()
        print(f"\n  投資焦點:")
        print(f"    長期競爭力: {focus['long_term_count']} 個影片")
        print(f"    短期市場: {focus['short_term_count']} 個影片")

        # 4.5 互動指標
        db.cursor.execute("""
            SELECT
                AVG(like_number) as avg_likes,
                AVG(comment_number) as avg_comments,
                MAX(like_number) as max_likes,
                MAX(comment_number) as max_comments
            FROM Youtuber_Financial_Data
        """)

        engagement = db.cursor.fetchone()
        print(f"\n  互動指標:")
        print(f"    平均按讚數: {engagement['avg_likes']:.0f}")
        print(f"    平均評論數: {engagement['avg_comments']:.0f}")
        print(f"    最高按讚數: {engagement['max_likes']:.0f}")
        print(f"    最高評論數: {engagement['max_comments']:.0f}")

        # 4.6 估值情緒
        db.cursor.execute("""
            SELECT
                AVG(valuation) as avg_valuation
            FROM Youtuber_Financial_Data
        """)

        valuation = db.cursor.fetchone()
        val_sentiment = "低估" if valuation['avg_valuation'] > 0 else "高估" if valuation['avg_valuation'] < 0 else "中性"
        print(f"\n  市場估值情緒:")
        print(f"    平均估值: {valuation['avg_valuation']:.3f} ({val_sentiment})")

    # 5. 熱門影片 Top 10
    print("\n【熱門影片 Top 10（按觀看次數）】")
    db.cursor.execute("""
        SELECT
            v.title,
            v.channel_name,
            v.view_count,
            v.like_count,
            v.comment_count,
            f.stock_ticker,
            f.video_sentiment
        FROM videos v
        LEFT JOIN Youtuber_Financial_Data f ON v.video_id = f.video_id
        ORDER BY v.view_count DESC
        LIMIT 10
    """)

    for idx, row in enumerate(db.cursor.fetchall(), 1):
        print(f"\n  [{idx}] {row['title'][:60]}")
        print(f"      頻道: {row['channel_name']}")
        print(f"      觀看: {row['view_count']:,} | 讚: {row['like_count']:,} | 評論: {row['comment_count']:,}")
        if row['stock_ticker']:
            sentiment_emoji = "📈" if row['video_sentiment'] > 0 else "📉" if row['video_sentiment'] < 0 else "➡️"
            print(f"      股票: {row['stock_ticker']} | 情感: {row['video_sentiment']:.2f} {sentiment_emoji}")

    # 6. 最近分析的影片
    print("\n【最近分析的影片（最新 5 個）】")
    db.cursor.execute("""
        SELECT
            v.title,
            v.channel_name,
            f.stock_ticker,
            f.video_sentiment,
            f.financial_ratio
        FROM Youtuber_Financial_Data f
        JOIN videos v ON f.video_id = v.video_id
        ORDER BY f.id DESC
        LIMIT 5
    """)

    for idx, row in enumerate(db.cursor.fetchall(), 1):
        print(f"\n  [{idx}] {row['title'][:60]}")
        print(f"      頻道: {row['channel_name']}")
        if row['stock_ticker']:
            print(f"      股票: {row['stock_ticker']} | 情感: {row['video_sentiment']:.2f} | 財務相關: {row['financial_ratio']:.2f}")

    print("\n" + "="*80)
    print("報告結束")
    print("="*80 + "\n")

    db.close()


if __name__ == '__main__':
    generate_statistics_report()
