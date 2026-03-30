#!/usr/bin/env python3
"""
創建多時間週期的 Single 資料庫
從現有 2years single db 複製資料，重新計算 return_rate, class, during
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.stock_price_fetcher import StockPriceFetcher
from dotenv import load_dotenv

load_dotenv()


def calculate_class(sentiment: float, return_rate: float) -> int:
    """
    計算分類標籤

    Args:
        sentiment: video_sentiment (-1 到 1)
        return_rate: 股票回報率 (小數形式)

    Returns:
        1 = 預測正確, -1 = 預測錯誤
    """
    threshold = 0.05  # 5% 閾值

    if sentiment > 0 and return_rate >= threshold:
        return 1  # 看漲且上漲 >= 5%
    elif sentiment == 0 and -threshold < return_rate < threshold:
        return 1  # 中性且波動 < 5%
    elif sentiment < 0 and return_rate <= -threshold:
        return 1  # 看跌且下跌 <= -5%
    else:
        return -1  # 預測錯誤


def create_period_database(source_db: str, target_db: str, months: int, youtuber_name: str):
    """
    創建指定時間週期的資料庫

    Args:
        source_db: 來源資料庫（2years single db）
        target_db: 目標資料庫
        months: 時間週期（月數）
        youtuber_name: YouTuber 名稱（用於顯示）
    """
    print(f"\n{'='*80}")
    print(f"創建 {months} 個月資料庫: {youtuber_name}")
    print(f"{'='*80}")
    print(f"來源: {source_db}")
    print(f"目標: {target_db}")

    # 檢查來源資料庫
    if not os.path.exists(source_db):
        print(f"❌ 來源資料庫不存在: {source_db}")
        return False

    # 複製資料庫
    print(f"\n1. 複製資料庫...")
    shutil.copy2(source_db, target_db)
    print(f"   ✓ 已複製")

    # 連接資料庫
    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()

    # 取得所有記錄
    cursor.execute("""
        SELECT id, stock_ticker, published_time, video_sentiment
        FROM Youtuber_Financial_Data
        WHERE stock_ticker IS NOT NULL
        ORDER BY id
    """)

    records = cursor.fetchall()
    print(f"\n2. 總記錄數: {len(records)}")

    # 初始化 StockPriceFetcher
    fetcher = StockPriceFetcher()

    # 統計
    success_count = 0
    fail_count = 0
    skip_count = 0

    print(f"\n3. 計算 {months} 個月回報率...")

    # 計算今天的日期
    today = datetime.now().date()

    for idx, (record_id, ticker, published_time, video_sentiment) in enumerate(records, 1):
        if idx % 50 == 0:
            print(f"   處理進度: {idx}/{len(records)}")

        try:
            # 解析發布日期（支援兩種格式）
            try:
                pub_date = datetime.strptime(published_time, '%Y-%m-%d').date()
            except ValueError:
                # 如果包含時間戳，使用完整格式
                pub_date = datetime.strptime(published_time, '%Y-%m-%d %H:%M:%S').date()

            # 計算評估日期
            eval_date = pub_date + relativedelta(months=months)

            # 檢查評估日期是否超過今天
            if eval_date > today:
                skip_count += 1
                # 設為 NULL（資料不足）
                cursor.execute("""
                    UPDATE Youtuber_Financial_Data
                    SET return_rate = NULL, class = NULL
                    WHERE id = ?
                """, (record_id,))
                continue

            # 計算回報率
            result = fetcher.calculate_custom_return(
                ticker=ticker,
                publish_date=published_time,
                months=months,
                threshold=0.05
            )

            if result is None:
                fail_count += 1
                # 設為 NULL（API 失敗）
                cursor.execute("""
                    UPDATE Youtuber_Financial_Data
                    SET return_rate = NULL, class = NULL
                    WHERE id = ?
                """, (record_id,))
                continue

            return_rate, _ = result

            # 計算 class
            class_value = calculate_class(video_sentiment, return_rate)

            # 計算 during（發布日期到評估日期的天數）
            during = (eval_date - pub_date).days

            # 更新資料庫
            cursor.execute("""
                UPDATE Youtuber_Financial_Data
                SET return_rate = ?, class = ?, during = ?
                WHERE id = ?
            """, (return_rate, class_value, during, record_id))

            success_count += 1

        except Exception as e:
            fail_count += 1
            print(f"   ✗ 記錄 {record_id} 失敗: {str(e)[:100]}")
            # 設為 NULL
            cursor.execute("""
                UPDATE Youtuber_Financial_Data
                SET return_rate = NULL, class = NULL
                WHERE id = ?
            """, (record_id,))

    # 刪除無效記錄（return_rate 為 NULL）
    print(f"\n4. 刪除無效記錄...")
    cursor.execute("DELETE FROM Youtuber_Financial_Data WHERE return_rate IS NULL")
    deleted_count = cursor.rowcount

    conn.commit()

    # 最終統計
    cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data")
    final_count = cursor.fetchone()[0]

    conn.close()

    # 顯示結果
    print(f"\n{'='*80}")
    print(f"處理完成")
    print(f"{'='*80}")
    print(f"成功: {success_count}")
    print(f"失敗: {fail_count}")
    print(f"跳過（時間不足）: {skip_count}")
    print(f"刪除無效記錄: {deleted_count}")
    print(f"最終記錄數: {final_count}")
    print(f"{'='*80}\n")

    return True


def main():
    print("="*80)
    print("創建多時間週期 Single 資料庫")
    print("="*80)

    # 定義要創建的資料庫
    databases = [
        # Tom Nash
        {
            'source': 'youtube_analysis_2years_single.db',
            'target': 'youtube_analysis_1month_single.db',
            'months': 1,
            'name': 'Tom Nash (1個月)'
        },
        {
            'source': 'youtube_analysis_2years_single.db',
            'target': 'youtube_analysis_6months_single.db',
            'months': 6,
            'name': 'Tom Nash (6個月)'
        },
        {
            'source': 'youtube_analysis_2years_single.db',
            'target': 'youtube_analysis_1year_single.db',
            'months': 12,
            'name': 'Tom Nash (1年)'
        },
        # Joseph (使用原始的 2years db，而不是 cleaned 版本)
        {
            'source': 'youtube_analysis_2years.db',  # 使用原始主資料庫
            'target': 'youtube_analysis_1month_single_joseph.db',
            'months': 1,
            'name': 'Joseph (1個月)',
            'youtuber_filter': 'Joseph Hogue'
        },
        {
            'source': 'youtube_analysis_2years.db',
            'target': 'youtube_analysis_6months_single_joseph.db',
            'months': 6,
            'name': 'Joseph (6個月)',
            'youtuber_filter': 'Joseph Hogue'
        },
        {
            'source': 'youtube_analysis_2years.db',
            'target': 'youtube_analysis_1year_single_joseph.db',
            'months': 12,
            'name': 'Joseph (1年)',
            'youtuber_filter': 'Joseph Hogue'
        },
    ]

    # 創建所有資料庫
    success_dbs = []
    failed_dbs = []

    for db_info in databases:
        try:
            result = create_period_database(
                source_db=db_info['source'],
                target_db=db_info['target'],
                months=db_info['months'],
                youtuber_name=db_info['name']
            )

            if result:
                success_dbs.append(db_info['target'])
            else:
                failed_dbs.append(db_info['target'])

        except Exception as e:
            print(f"\n❌ 創建 {db_info['target']} 時發生錯誤: {e}")
            failed_dbs.append(db_info['target'])

    # 總結
    print("\n" + "="*80)
    print("所有資料庫創建完成")
    print("="*80)
    print(f"\n成功創建: {len(success_dbs)} 個")
    for db in success_dbs:
        size = os.path.getsize(db) / 1024 / 1024
        print(f"  ✓ {db} ({size:.2f} MB)")

    if failed_dbs:
        print(f"\n失敗: {len(failed_dbs)} 個")
        for db in failed_dbs:
            print(f"  ✗ {db}")

    print(f"\n{'='*80}")
    print("注意: comment_sentiment 欄位目前為 0，之後需統一分析")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
