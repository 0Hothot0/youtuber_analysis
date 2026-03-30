#!/usr/bin/env python3
"""
Comment Sentiment 狀態報告工具
快速查看所有 single 資料庫的 comment_sentiment 處理進度
"""

import sqlite3
import os
from typing import Dict, List
from datetime import datetime


def get_detailed_stats(db_path: str) -> Dict:
    """取得資料庫詳細統計"""
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 基本統計
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN comment_sentiment IS NULL THEN 1 END) as null_count,
            COUNT(CASE WHEN comment_sentiment = 0 THEN 1 END) as zero_count,
            COUNT(CASE WHEN comment_sentiment > 0 THEN 1 END) as positive,
            COUNT(CASE WHEN comment_sentiment < 0 THEN 1 END) as negative,
            COUNT(DISTINCT video_id) as unique_videos,
            AVG(CASE WHEN comment_sentiment IS NOT NULL AND comment_sentiment != 0
                THEN comment_sentiment END) as avg_sentiment
        FROM Youtuber_Financial_Data
    """)

    result = cursor.fetchone()

    # 情緒分佈
    cursor.execute("""
        SELECT
            CASE
                WHEN comment_sentiment IS NULL THEN 'NULL (未處理/留言關閉)'
                WHEN comment_sentiment = 0 THEN '0.0 (無留言)'
                WHEN comment_sentiment < -0.5 THEN '非常負面 (< -0.5)'
                WHEN comment_sentiment < 0 THEN '負面 (-0.5 ~ 0)'
                WHEN comment_sentiment < 0.5 THEN '正面 (0 ~ 0.5)'
                ELSE '非常正面 (>= 0.5)'
            END as sentiment_range,
            COUNT(*) as count
        FROM Youtuber_Financial_Data
        GROUP BY sentiment_range
        ORDER BY
            CASE
                WHEN comment_sentiment IS NULL THEN 0
                WHEN comment_sentiment = 0 THEN 1
                ELSE 2
            END,
            comment_sentiment
    """)

    distribution = cursor.fetchall()

    conn.close()

    return {
        'total': result[0],
        'null_count': result[1],
        'zero_count': result[2],
        'positive': result[3],
        'negative': result[4],
        'unique_videos': result[5],
        'avg_sentiment': result[6] if result[6] else 0,
        'distribution': distribution,
        'pending': result[1] + result[2],  # NULL + 0 都算待處理
        'completed': result[3] + result[4]  # 正面 + 負面
    }


def print_progress_bar(current: int, total: int, width: int = 40) -> str:
    """生成進度條"""
    if total == 0:
        return "[" + "="*width + "] 100%"

    percentage = current / total
    filled = int(width * percentage)
    bar = "=" * filled + "-" * (width - filled)
    return f"[{bar}] {percentage*100:.1f}%"


def main():
    databases = [
        ("Joseph 2年期", "youtube_analysis_2years_single_joseph.db"),
        ("Joseph 3個月", "youtube_analysis_3months_single_joseph.db"),
        ("Single 2年期", "youtube_analysis_2years_single.db"),
        ("Single 3個月", "youtube_analysis_3months_single.db")
    ]

    print("\n" + "="*80)
    print("Comment Sentiment 處理狀態報告")
    print("="*80)
    print(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    total_records = 0
    total_completed = 0
    total_pending = 0

    for name, db_path in databases:
        stats = get_detailed_stats(db_path)

        if stats is None:
            print(f"\n⚠ {name}: 資料庫不存在")
            continue

        print(f"\n📊 {name} ({db_path})")
        print("-"*80)

        # 基本統計
        print(f"總記錄數: {stats['total']:,}")
        print(f"唯一影片數: {stats['unique_videos']:,}")
        print()

        # 處理進度
        print("處理進度:")
        print(f"  已完成: {stats['completed']:,} ({stats['completed']/stats['total']*100:.1f}%)")
        print(f"  待處理: {stats['pending']:,} ({stats['pending']/stats['total']*100:.1f}%)")
        print(f"  進度條: {print_progress_bar(stats['completed'], stats['total'])}")
        print()

        # 情緒統計
        if stats['completed'] > 0:
            print("情緒統計 (已分析的影片):")
            print(f"  正面留言: {stats['positive']:,}")
            print(f"  負面留言: {stats['negative']:,}")
            print(f"  平均情緒: {stats['avg_sentiment']:.3f}")
            print()

        # 詳細分佈
        print("詳細分佈:")
        for sentiment_range, count in stats['distribution']:
            percentage = count / stats['total'] * 100
            bar = print_progress_bar(count, stats['total'], width=30)
            print(f"  {sentiment_range:30s}: {count:4,} ({percentage:5.1f}%) {bar}")

        total_records += stats['total']
        total_completed += stats['completed']
        total_pending += stats['pending']

    # 總結
    print("\n" + "="*80)
    print("總結")
    print("="*80)
    print(f"所有資料庫總記錄數: {total_records:,}")
    print(f"已完成: {total_completed:,} ({total_completed/total_records*100:.1f}%)")
    print(f"待處理: {total_pending:,} ({total_pending/total_records*100:.1f}%)")
    print(f"總體進度: {print_progress_bar(total_completed, total_records)}")
    print("="*80)

    # 預估時間
    if total_pending > 0:
        # 每個影片約需 10-15 秒 (YouTube API + Gemini API + 延遲)
        avg_time_per_video = 12
        estimated_minutes = (total_pending * avg_time_per_video) / 60
        estimated_hours = estimated_minutes / 60

        print(f"\n⏱ 預估完成時間:")
        if estimated_hours < 1:
            print(f"  約 {estimated_minutes:.0f} 分鐘")
        else:
            print(f"  約 {estimated_hours:.1f} 小時 ({estimated_minutes:.0f} 分鐘)")
        print()

    print()


if __name__ == "__main__":
    main()
