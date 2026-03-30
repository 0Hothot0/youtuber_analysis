#!/usr/bin/env python3
"""
創建多時間週期的 Fin Tek 資料庫
從原始 2years db 提取 Fin Tek 資料，重新計算 return_rate, class, during
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.stock_price_fetcher import StockPriceFetcher
from dotenv import load_dotenv

load_dotenv()


def parse_date(date_string):
    """解析日期，支援多種格式"""
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"無法解析日期: {date_string}")


def calculate_class(sentiment: float, return_rate: float) -> int:
    """計算分類標籤"""
    threshold = 0.05

    if sentiment > 0 and return_rate >= threshold:
        return 1
    elif sentiment == 0 and -threshold < return_rate < threshold:
        return 1
    elif sentiment < 0 and return_rate <= -threshold:
        return 1
    else:
        return -1


def create_fintek_db(source_db: str, target_db: str, months: int):
    """創建 Fin Tek 資料庫"""
    print(f"\n{'='*80}")
    print(f"創建 Fin Tek {months} 個月資料庫")
    print(f"{'='*80}")
    print(f"來源: {source_db}")
    print(f"目標: {target_db}")

    if not os.path.exists(source_db):
        print(f"❌ 來源資料庫不存在")
        return False

    # 連接來源資料庫
    source_conn = sqlite3.connect(source_db)
    source_cursor = source_conn.cursor()

    # 檢查是否有 published_time 欄位
    source_cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
    columns = [col[1] for col in source_cursor.fetchall()]

    if 'published_time' not in columns:
        print(f"❌ 來源資料庫缺少 published_time 欄位")
        source_conn.close()
        return False

    # 取得 Fin Tek 的記錄
    print(f"\n1. 提取 Fin Tek 資料...")
    source_cursor.execute("""
        SELECT id, stock_ticker, published_time, video_sentiment
        FROM Youtuber_Financial_Data
        WHERE stock_ticker IS NOT NULL
        AND video_id IN (
            SELECT video_id FROM videos WHERE channel_name = 'Fin Tek'
        )
    """)

    fintek_records = source_cursor.fetchall()
    print(f"   找到 {len(fintek_records)} 筆記錄")

    if len(fintek_records) == 0:
        print(f"❌ 沒有找到 Fin Tek 的記錄")
        source_conn.close()
        return False

    # 創建目標資料庫（複製結構）
    print(f"\n2. 創建目標資料庫...")
    shutil.copy2(source_db, target_db)

    # 連接目標資料庫
    target_conn = sqlite3.connect(target_db)
    target_cursor = target_conn.cursor()

    # 清空目標資料庫，只保留 Fin Tek 的記錄
    target_cursor.execute("DELETE FROM Youtuber_Financial_Data")
    target_conn.commit()

    # 複製 Fin Tek 記錄
    source_cursor.execute("""
        SELECT * FROM Youtuber_Financial_Data
        WHERE video_id IN (
            SELECT video_id FROM videos WHERE channel_name = 'Fin Tek'
        )
    """)
    fintek_full_records = source_cursor.fetchall()

    # 取得欄位名稱
    column_names = [desc[0] for desc in source_cursor.description]
    placeholders = ','.join(['?' for _ in column_names])

    target_cursor.executemany(
        f"INSERT INTO Youtuber_Financial_Data ({','.join(column_names)}) VALUES ({placeholders})",
        fintek_full_records
    )
    target_conn.commit()

    print(f"   ✓ 已複製 {len(fintek_full_records)} 筆記錄")

    source_conn.close()

    # 重新計算 return_rate, class, during
    print(f"\n3. 計算 {months} 個月回報率...")

    fetcher = StockPriceFetcher()
    today = datetime.now().date()

    success = 0
    fail = 0
    skip = 0

    # 取得需要更新的記錄
    target_cursor.execute("""
        SELECT id, stock_ticker, published_time, video_sentiment
        FROM Youtuber_Financial_Data
        WHERE stock_ticker IS NOT NULL
    """)
    records = target_cursor.fetchall()

    for idx, (record_id, ticker, published_time, sentiment) in enumerate(records, 1):
        if idx % 20 == 0:
            print(f"   進度: {idx}/{len(records)}")

        try:
            # 解析日期
            pub_date = parse_date(published_time)
            eval_date = pub_date + relativedelta(months=months)

            # 檢查時間
            if eval_date > today:
                skip += 1
                target_cursor.execute("UPDATE Youtuber_Financial_Data SET return_rate=NULL, class=NULL WHERE id=?", (record_id,))
                continue

            # 計算回報率
            result = fetcher.calculate_custom_return(ticker, str(pub_date), months, 0.05)

            if result is None:
                fail += 1
                target_cursor.execute("UPDATE Youtuber_Financial_Data SET return_rate=NULL, class=NULL WHERE id=?", (record_id,))
                continue

            return_rate, _ = result
            class_value = calculate_class(sentiment, return_rate)
            during = (eval_date - pub_date).days

            target_cursor.execute("""
                UPDATE Youtuber_Financial_Data
                SET return_rate=?, class=?, during=?
                WHERE id=?
            """, (return_rate, class_value, during, record_id))

            success += 1

        except Exception as e:
            fail += 1
            target_cursor.execute("UPDATE Youtuber_Financial_Data SET return_rate=NULL, class=NULL WHERE id=?", (record_id,))

    # 刪除無效記錄
    print(f"\n4. 刪除無效記錄...")
    target_cursor.execute("DELETE FROM Youtuber_Financial_Data WHERE return_rate IS NULL")
    deleted = target_cursor.rowcount

    target_conn.commit()

    target_cursor.execute("SELECT COUNT(*) FROM Youtuber_Financial_Data")
    final_count = target_cursor.fetchone()[0]

    target_conn.close()

    print(f"\n{'='*80}")
    print(f"完成")
    print(f"{'='*80}")
    print(f"成功: {success}")
    print(f"失敗: {fail}")
    print(f"跳過: {skip}")
    print(f"刪除: {deleted}")
    print(f"最終記錄數: {final_count}")
    print(f"{'='*80}\n")

    return final_count > 0


def main():
    print("="*80)
    print("創建多時間週期 Fin Tek 資料庫")
    print("="*80)

    # 創建輸出目錄
    output_dir = Path('fin_tek')
    output_dir.mkdir(exist_ok=True)
    print(f"\n輸出目錄: {output_dir.absolute()}\n")

    # 定義任務 - 5 個時間周期
    tasks = [
        ('youtube_analysis_2years.db', 'fin_tek/youtube_analysis_1month_single_fintek.db', 1),
        ('youtube_analysis_2years.db', 'fin_tek/youtube_analysis_3months_single_fintek.db', 3),
        ('youtube_analysis_2years.db', 'fin_tek/youtube_analysis_6months_single_fintek.db', 6),
        ('youtube_analysis_2years.db', 'fin_tek/youtube_analysis_1year_single_fintek.db', 12),
        ('youtube_analysis_2years.db', 'fin_tek/youtube_analysis_2years_single_fintek.db', 24),
    ]

    results = []

    for source, target, months in tasks:
        success = create_fintek_db(source, target, months)
        results.append((target, success))

    # 總結
    print("\n" + "="*80)
    print("Fin Tek 資料庫創建完成")
    print("="*80)

    for db, success in results:
        if success:
            if os.path.exists(db):
                size = os.path.getsize(db) / 1024 / 1024
                print(f"  ✓ {db} ({size:.2f} MB)")
            else:
                print(f"  ✗ {db} (文件不存在)")
        else:
            print(f"  ✗ {db} (失敗)")

    print("\n" + "="*80)
    print("注意: comment_sentiment 欄位目前為 0，之後需統一分析")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
