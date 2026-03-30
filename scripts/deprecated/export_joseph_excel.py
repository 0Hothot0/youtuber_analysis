#!/usr/bin/env python3
"""
匯出 Joseph 所有資料庫到 Excel
包含 clean, train, test 版本
"""

import sqlite3
import pandas as pd
import os
from sklearn.model_selection import train_test_split

# Joseph 的資料庫列表
DATABASES = [
    ('joseph/youtube_analysis_2years_single_joseph.db', 'joseph_2years'),
    ('joseph/youtube_analysis_3months_single_joseph.db', 'joseph_3months'),
    ('joseph/youtube_analysis_1month_single_joseph.db', 'joseph_1month'),
    ('joseph/youtube_analysis_6months_single_joseph.db', 'joseph_6months'),
    ('joseph/youtube_analysis_1year_single_joseph.db', 'joseph_1year'),
]

# 需要保留的欄位（18個）
FEATURE_COLUMNS = [
    'id',
    'video_uuid',
    'video_id',
    'stock_ticker',
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

def export_database(db_path, output_prefix):
    """匯出單一資料庫"""
    print(f"\n處理: {db_path}")

    if not os.path.exists(db_path):
        print(f"  ✗ 資料庫不存在")
        return False

    # 連接資料庫
    conn = sqlite3.connect(db_path)

    # 讀取資料
    query = f"SELECT {', '.join(FEATURE_COLUMNS)} FROM Youtuber_Financial_Data ORDER BY id"
    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"  記錄數: {len(df)}")

    # 統計
    class_dist = df['class'].value_counts()
    print(f"  Class 分佈:")
    print(f"    Class 1: {class_dist.get(1, 0)} ({class_dist.get(1, 0)/len(df)*100:.1f}%)")
    print(f"    Class -1: {class_dist.get(-1, 0)} ({class_dist.get(-1, 0)/len(df)*100:.1f}%)")

    # 匯出 clean 版本
    clean_file = f"{output_prefix}_clean.xlsx"
    with pd.ExcelWriter(clean_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Financial_Data', index=False)
    print(f"  ✓ {clean_file}")

    # Train/Test 分割（80/20, Stratified）
    train_df, test_df = train_test_split(
        df,
        test_size=0.2,
        random_state=42,
        stratify=df['class']
    )

    print(f"  Train: {len(train_df)} 筆")
    print(f"  Test: {len(test_df)} 筆")

    # 匯出 train 版本
    train_file = f"{output_prefix}_train.xlsx"
    with pd.ExcelWriter(train_file, engine='openpyxl') as writer:
        train_df.to_excel(writer, sheet_name='Training_Data', index=False)
    print(f"  ✓ {train_file}")

    # 匯出 test 版本
    test_file = f"{output_prefix}_test.xlsx"
    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        test_df.to_excel(writer, sheet_name='Test_Data', index=False)
    print(f"  ✓ {test_file}")

    return True


def main():
    print("="*80)
    print("Joseph 資料庫匯出到 Excel")
    print("="*80)

    # 創建輸出目錄
    os.makedirs('exports/joseph', exist_ok=True)

    success_count = 0

    for db_path, output_name in DATABASES:
        output_prefix = f'exports/joseph/{output_name}'

        if export_database(db_path, output_prefix):
            success_count += 1

    # 總結
    print(f"\n{'='*80}")
    print(f"匯出完成")
    print(f"{'='*80}")
    print(f"成功: {success_count}/{len(DATABASES)}")
    print(f"輸出目錄: exports/joseph/")
    print(f"{'='*80}")

    # 列出生成的檔案
    print(f"\n生成的檔案:")
    excel_files = sorted([f for f in os.listdir('exports/joseph') if f.endswith('.xlsx')])
    for f in excel_files:
        size = os.path.getsize(f'exports/joseph/{f}') / 1024
        print(f"  {f:50s} ({size:.1f} KB)")

    print()


if __name__ == "__main__":
    main()
