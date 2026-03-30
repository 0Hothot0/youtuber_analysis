#!/usr/bin/env python3
"""
匯出 Invest with Henry 和 Paul Thomas 到 Excel（11 個特徵）
"""

import sqlite3
import pandas as pd
import os
from sklearn.preprocessing import StandardScaler

# 用戶指定的 11 個特徵
SELECTED_COLUMNS = [
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
]

# 需要標準化的欄位
COLUMNS_TO_STANDARDIZE = ['like_number', 'comment_number', 'view_number']

# 數據庫列表
DATABASES = {
    'Invest with Henry': [
        ('invest_with_henry/youtube_analysis_1month_single_henry.db', 'henry_1month'),
        ('invest_with_henry/youtube_analysis_3months_single_henry.db', 'henry_3months'),
        ('invest_with_henry/youtube_analysis_6months_single_henry.db', 'henry_6months'),
        ('invest_with_henry/youtube_analysis_1year_single_henry.db', 'henry_1year'),
        ('invest_with_henry/youtube_analysis_2years_single_henry.db', 'henry_2years'),
    ],
    'Paul Thomas': [
        ('paul_thomas/youtube_analysis_1month_single_paul.db', 'paul_1month'),
        ('paul_thomas/youtube_analysis_3months_single_paul.db', 'paul_3months'),
        ('paul_thomas/youtube_analysis_6months_single_paul.db', 'paul_6months'),
        ('paul_thomas/youtube_analysis_1year_single_paul.db', 'paul_1year'),
        ('paul_thomas/youtube_analysis_2years_single_paul.db', 'paul_2years'),
    ]
}


def standardize_columns(df, columns_to_std):
    """標準化指定欄位"""
    df_copy = df.copy()
    existing_cols = [col for col in columns_to_std if col in df_copy.columns]

    if not existing_cols:
        return df_copy

    scaler = StandardScaler()
    df_copy[existing_cols] = scaler.fit_transform(df_copy[existing_cols])

    return df_copy


def export_database(db_path, output_file, youtuber_name):
    """匯出單一資料庫"""
    print(f"\n處理: {db_path}")

    if not os.path.exists(db_path):
        print(f"  ✗ 資料庫不存在")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 檢查哪些欄位存在
    cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
    available_columns = [col[1] for col in cursor.fetchall()]

    existing_columns = [col for col in SELECTED_COLUMNS if col in available_columns]
    missing_columns = [col for col in SELECTED_COLUMNS if col not in available_columns]

    if missing_columns:
        print(f"  ⚠️  缺少欄位: {', '.join(missing_columns)}")

    print(f"  ✓ 可用欄位: {len(existing_columns)}/{len(SELECTED_COLUMNS)}")

    # 讀取資料
    query = f"SELECT {', '.join(existing_columns)} FROM Youtuber_Financial_Data ORDER BY id"
    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"  記錄數: {len(df)}")
    print(f"  特徵數: {len(df.columns)}")

    # 標準化
    existing_std_cols = [col for col in COLUMNS_TO_STANDARDIZE if col in df.columns]
    print(f"  標準化欄位: {', '.join(existing_std_cols)}")

    df_std = standardize_columns(df, COLUMNS_TO_STANDARDIZE)

    # 匯出
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_std.to_excel(writer, sheet_name=youtuber_name, index=False)

    print(f"  ✓ {output_file}")

    return True


def main():
    print("="*80)
    print("匯出 Invest with Henry 和 Paul Thomas 到 Excel（11 個特徵）")
    print("="*80)
    print(f"\n選擇的特徵:")
    for i, col in enumerate(SELECTED_COLUMNS, 1):
        print(f"  {i:2d}. {col}")
    print(f"\n標準化欄位: {', '.join(COLUMNS_TO_STANDARDIZE)}")
    print("="*80)

    # 創建輸出目錄
    os.makedirs('exports/henry_paul_11features', exist_ok=True)

    success_count = 0
    total_count = 0

    for youtuber_name, databases in DATABASES.items():
        print(f"\n\n{'='*80}")
        print(f"{youtuber_name}")
        print(f"{'='*80}")

        for db_path, output_name in databases:
            total_count += 1
            output_file = f'exports/henry_paul_11features/{output_name}.xlsx'

            if export_database(db_path, output_file, youtuber_name.replace(' ', '_')):
                success_count += 1

    # 總結
    print(f"\n{'='*80}")
    print(f"匯出完成")
    print(f"{'='*80}")
    print(f"成功: {success_count}/{total_count}")
    print(f"輸出目錄: exports/henry_paul_11features/")
    print(f"{'='*80}")

    # 列出生成的檔案
    print(f"\n生成的檔案:")
    excel_files = sorted([f for f in os.listdir('exports/henry_paul_11features') if f.endswith('.xlsx')])
    for f in excel_files:
        size = os.path.getsize(f'exports/henry_paul_11features/{f}') / 1024
        print(f"  {f:40s} ({size:.1f} KB)")

    print(f"\n{'='*80}")
    print("注意事項:")
    print("  • 只包含 11 個特徵（無 target variable）")
    print("  • like_number, comment_number, view_number 已標準化")
    print("  • 每個文件包含完整數據（無 train/test 切分）")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
