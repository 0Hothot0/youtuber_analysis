#!/usr/bin/env python3
"""
重新計算 during 欄位
改為：發布日期到今天的天數
"""

import sqlite3
import os
from datetime import datetime, date

# 所有資料庫
DATABASES = [
    'tom_nash/youtube_analysis_2years_single.db',
    'tom_nash/youtube_analysis_3months_single.db',
    'tom_nash/youtube_analysis_1month_single.db',
    'tom_nash/youtube_analysis_6months_single.db',
    'tom_nash/youtube_analysis_1year_single.db',
    'joseph/youtube_analysis_2years_single_joseph.db',
    'joseph/youtube_analysis_3months_single_joseph.db',
    'joseph/youtube_analysis_1month_single_joseph.db',
    'joseph/youtube_analysis_6months_single_joseph.db',
    'joseph/youtube_analysis_1year_single_joseph.db',
]


def parse_date(date_string):
    """解析日期"""
    formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d']

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"無法解析日期: {date_string}")


def update_during(db_path):
    """更新資料庫的 during 欄位"""
    print(f"\n處理: {db_path}")

    if not os.path.exists(db_path):
        print(f"  ✗ 資料庫不存在")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 檢查是否有 published_time 欄位
    cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
    columns = [col[1] for col in cursor.fetchall()]

    has_published_time = 'published_time' in columns

    if has_published_time:
        # 直接從資料庫讀取
        cursor.execute("""
            SELECT id, published_time
            FROM Youtuber_Financial_Data
        """)
        records = cursor.fetchall()
    else:
        # Joseph 的資料庫沒有 published_time，需要從主資料庫取得
        print(f"  ⚠ 無 published_time 欄位，從主資料庫讀取...")

        # 連接主資料庫
        main_conn = sqlite3.connect('youtube_analysis_2years.db')
        main_cursor = main_conn.cursor()

        # 取得 video_id 對應的 published_time
        cursor.execute("SELECT id, video_id FROM Youtuber_Financial_Data")
        video_ids = cursor.fetchall()

        records = []
        for record_id, video_id in video_ids:
            main_cursor.execute("""
                SELECT published_at
                FROM videos
                WHERE video_id = ?
            """, (video_id,))

            result = main_cursor.fetchone()
            if result:
                records.append((record_id, result[0]))

        main_conn.close()

    today = date.today()
    print(f"  記錄數: {len(records)}")

    updated = 0
    errors = 0

    for record_id, published_time in records:
        try:
            pub_date = parse_date(published_time)

            # 計算從發布到今天的天數
            during = (today - pub_date).days

            # 更新資料庫
            cursor.execute("""
                UPDATE Youtuber_Financial_Data
                SET during = ?
                WHERE id = ?
            """, (during, record_id))

            updated += 1

        except Exception as e:
            errors += 1
            print(f"  ✗ ID {record_id} 錯誤: {e}")

    conn.commit()

    # 顯示統計
    cursor.execute("SELECT MIN(during), MAX(during), AVG(during) FROM Youtuber_Financial_Data")
    min_d, max_d, avg_d = cursor.fetchone()

    print(f"  ✓ 更新: {updated} 筆")
    if errors > 0:
        print(f"  ✗ 錯誤: {errors} 筆")
    print(f"  During 範圍: {min_d} - {max_d} 天 (平均: {avg_d:.1f} 天)")

    conn.close()
    return True


def main():
    print("="*80)
    print("重新計算 during 欄位")
    print(f"計算方式: 發布日期 到 今天 ({date.today()}) 的天數")
    print("="*80)

    success = 0

    for db_path in DATABASES:
        if update_during(db_path):
            success += 1

    print(f"\n{'='*80}")
    print(f"完成")
    print(f"{'='*80}")
    print(f"成功更新: {success}/{len(DATABASES)} 個資料庫")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
