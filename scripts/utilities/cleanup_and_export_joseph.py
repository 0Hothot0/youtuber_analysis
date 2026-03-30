#!/usr/bin/env python3
"""
清理 Joseph 資料庫並輸出 Excel
只保留指定的欄位
"""

import sqlite3
import pandas as pd
import os
import shutil
from datetime import datetime

# 需要保留的欄位
KEEP_COLUMNS = [
    'like_number',
    'comment_number',
    'view_number',
    'text_type',
    'video_sentiment',
    'comment_sentiment',
    'financial_ratio',
    'celebrity',
    'relevancy',
    'long_term_competitiveness',
    'short_term_focus',
    'stock_price_growth_trend',
    'during',
    'class'
]

# 識別欄位（需要但不在上面列表中）
ID_COLUMNS = ['id', 'video_uuid', 'video_id', 'stock_ticker']

# 完整保留列表
ALL_KEEP_COLUMNS = ID_COLUMNS + KEEP_COLUMNS


def backup_database(db_path):
    """備份原始資料庫"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"✓ 備份資料庫: {backup_path}")
    return backup_path


def get_all_columns(db_path):
    """取得資料庫所有欄位"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(Youtuber_Financial_Data)')
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()
    return columns


def cleanup_database(db_path):
    """清理資料庫，只保留指定欄位"""
    print(f"\n處理資料庫: {db_path}")

    # 取得所有欄位
    all_columns = get_all_columns(db_path)
    print(f"  原始欄位數: {len(all_columns)}")

    # 找出需要刪除的欄位
    columns_to_drop = [col for col in all_columns if col not in ALL_KEEP_COLUMNS]
    print(f"  需要刪除: {len(columns_to_drop)} 個欄位")

    if not columns_to_drop:
        print(f"  ✓ 資料庫已經是乾淨的")
        return

    # 建立新表結構
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 取得需要保留的欄位及其類型
    cursor.execute('PRAGMA table_info(Youtuber_Financial_Data)')
    all_cols_info = cursor.fetchall()
    keep_cols_info = [col for col in all_cols_info if col[1] in ALL_KEEP_COLUMNS]

    # 建立新表
    new_table_cols = []
    for col in keep_cols_info:
        col_name = col[1]
        col_type = col[2]
        not_null = 'NOT NULL' if col[3] else ''

        # 特殊處理
        if col_name == 'id':
            new_table_cols.append(f"{col_name} INTEGER PRIMARY KEY AUTOINCREMENT")
        elif col_name == 'video_uuid':
            new_table_cols.append(f"{col_name} TEXT NOT NULL")
        else:
            new_table_cols.append(f"{col_name} {col_type} {not_null}".strip())

    new_table_sql = f"""
    CREATE TABLE Youtuber_Financial_Data_new (
        {', '.join(new_table_cols)}
    )
    """

    print(f"  建立新表...")
    cursor.execute(new_table_sql)

    # 複製資料
    keep_columns_str = ', '.join([col for col in ALL_KEEP_COLUMNS if col in all_columns])
    print(f"  複製資料...")
    cursor.execute(f"""
        INSERT INTO Youtuber_Financial_Data_new ({keep_columns_str})
        SELECT {keep_columns_str}
        FROM Youtuber_Financial_Data
    """)

    # 刪除舊表，重命名新表
    cursor.execute('DROP TABLE Youtuber_Financial_Data')
    cursor.execute('ALTER TABLE Youtuber_Financial_Data_new RENAME TO Youtuber_Financial_Data')

    # 建立索引
    cursor.execute('CREATE INDEX idx_video_id ON Youtuber_Financial_Data(video_id)')
    cursor.execute('CREATE INDEX idx_video_uuid ON Youtuber_Financial_Data(video_uuid)')

    conn.commit()
    conn.close()

    print(f"  ✓ 清理完成")
    print(f"  保留欄位數: {len(ALL_KEEP_COLUMNS)}")


def export_to_excel(db_path, excel_path):
    """匯出資料庫到 Excel"""
    print(f"\n匯出到 Excel: {excel_path}")

    conn = sqlite3.connect(db_path)

    # 讀取資料
    query = f"SELECT {', '.join(ALL_KEEP_COLUMNS)} FROM Youtuber_Financial_Data ORDER BY id"
    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"  記錄數: {len(df)}")
    print(f"  欄位數: {len(df.columns)}")

    # 匯出到 Excel
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Financial_Data', index=False)

    file_size = os.path.getsize(excel_path) / 1024 / 1024
    print(f"  ✓ 匯出完成 ({file_size:.2f} MB)")

    # 顯示統計
    print(f"\n  資料統計:")
    print(f"    唯一影片數: {df['video_id'].nunique()}")
    print(f"    唯一股票數: {df['stock_ticker'].nunique()}")
    print(f"    已分析留言: {(df['comment_sentiment'] != 0).sum()} / {len(df)}")

    return df


def main():
    print("="*80)
    print("Joseph 資料庫清理與匯出工具")
    print("="*80)

    # Joseph 資料庫列表
    databases = [
        ('youtube_analysis_2years_single_joseph.db', 'joseph_2years_clean.xlsx'),
        ('youtube_analysis_3months_single_joseph.db', 'joseph_3months_clean.xlsx')
    ]

    for db_path, excel_path in databases:
        if not os.path.exists(db_path):
            print(f"\n⚠ 資料庫不存在: {db_path}")
            continue

        print(f"\n{'='*80}")
        print(f"處理: {db_path}")
        print(f"{'='*80}")

        # 備份
        backup_path = backup_database(db_path)

        # 清理
        cleanup_database(db_path)

        # 匯出
        df = export_to_excel(db_path, excel_path)

        print(f"\n✓ 完成: {excel_path}")

    print(f"\n{'='*80}")
    print("所有資料庫處理完成")
    print("="*80)

    # 顯示檔案列表
    print("\n生成的檔案:")
    for db_path, excel_path in databases:
        if os.path.exists(excel_path):
            size = os.path.getsize(excel_path) / 1024 / 1024
            print(f"  ✓ {excel_path} ({size:.2f} MB)")

    print("\n備份檔案:")
    backup_files = [f for f in os.listdir('.') if 'joseph.db.backup_' in f]
    for backup in sorted(backup_files)[-2:]:  # 只顯示最新的兩個
        size = os.path.getsize(backup) / 1024 / 1024
        print(f"  ✓ {backup} ({size:.2f} MB)")

    print()


if __name__ == "__main__":
    main()
