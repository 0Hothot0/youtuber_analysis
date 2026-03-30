#!/usr/bin/env python3
"""
匯出 Invest with Henry 和 Paul Thomas 到 Excel（11 個特徵 + Train/Test 切分）
每個文件包含兩個 sheet: Training_Data 和 Test_Data
"""

import sqlite3
import pandas as pd
import os
from sklearn.model_selection import train_test_split
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


def standardize_columns(df, columns_to_std, scaler=None, fit=True):
    """標準化指定欄位"""
    df_copy = df.copy()
    existing_cols = [col for col in columns_to_std if col in df_copy.columns]

    if not existing_cols:
        return df_copy, scaler

    if scaler is None:
        scaler = StandardScaler()

    if fit:
        df_copy[existing_cols] = scaler.fit_transform(df_copy[existing_cols])
    else:
        df_copy[existing_cols] = scaler.transform(df_copy[existing_cols])

    return df_copy, scaler


def export_database(db_path, output_file, youtuber_name):
    """匯出單一資料庫（含 Train/Test 切分）"""
    print(f"\n處理: {db_path}")

    if not os.path.exists(db_path):
        print(f"  ✗ 資料庫不存在")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 檢查哪些欄位存在
    cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
    available_columns = [col[1] for col in cursor.fetchall()]

    # 需要 class 欄位來做 stratified split
    if 'class' not in available_columns:
        print(f"  ✗ 缺少 class 欄位，無法進行 stratified split")
        conn.close()
        return False

    existing_columns = [col for col in SELECTED_COLUMNS if col in available_columns]
    missing_columns = [col for col in SELECTED_COLUMNS if col not in available_columns]

    if missing_columns:
        print(f"  ⚠️  缺少欄位: {', '.join(missing_columns)}")

    # 讀取資料（包含 class 用於切分）
    columns_with_class = existing_columns + ['class']
    query = f"SELECT {', '.join(columns_with_class)} FROM Youtuber_Financial_Data ORDER BY id"
    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"  記錄數: {len(df)}")
    print(f"  特徵數: {len(existing_columns)}")

    # Train/Test 切分（80/20, Stratified）
    train_df, test_df = train_test_split(
        df,
        test_size=0.2,
        random_state=42,
        stratify=df['class']
    )

    print(f"  Train: {len(train_df)} 筆 (80%)")
    print(f"  Test: {len(test_df)} 筆 (20%)")

    # 移除 class 欄位（只保留 11 個特徵）
    train_features = train_df[existing_columns]
    test_features = test_df[existing_columns]

    # 標準化（使用 train set 的統計數據）
    existing_std_cols = [col for col in COLUMNS_TO_STANDARDIZE if col in train_features.columns]
    print(f"  標準化欄位: {', '.join(existing_std_cols)}")

    train_std, scaler = standardize_columns(train_features, COLUMNS_TO_STANDARDIZE, fit=True)
    test_std, _ = standardize_columns(test_features, COLUMNS_TO_STANDARDIZE, scaler=scaler, fit=False)

    # 顯示標準化統計
    for col in existing_std_cols:
        mean = train_std[col].mean()
        std = train_std[col].std()
        print(f"    {col}: mean={mean:.4f}, std={std:.4f}")

    # 匯出到 Excel（兩個 sheet）
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        train_std.to_excel(writer, sheet_name='Training_Data', index=False)
        test_std.to_excel(writer, sheet_name='Test_Data', index=False)

    print(f"  ✓ {output_file}")

    return True


def main():
    print("="*80)
    print("匯出 Invest with Henry 和 Paul Thomas 到 Excel")
    print("11 個特徵 + Train/Test 切分")
    print("="*80)
    print(f"\n選擇的特徵:")
    for i, col in enumerate(SELECTED_COLUMNS, 1):
        print(f"  {i:2d}. {col}")
    print(f"\n標準化欄位: {', '.join(COLUMNS_TO_STANDARDIZE)}")
    print(f"切分方式: Stratified Random Split (80/20)")
    print(f"Random seed: 42")
    print("="*80)

    # 創建輸出目錄
    os.makedirs('exports/henry_paul_traintest', exist_ok=True)

    success_count = 0
    total_count = 0

    for youtuber_name, databases in DATABASES.items():
        print(f"\n\n{'='*80}")
        print(f"{youtuber_name}")
        print(f"{'='*80}")

        for db_path, output_name in databases:
            total_count += 1
            output_file = f'exports/henry_paul_traintest/{output_name}.xlsx'

            if export_database(db_path, output_file, youtuber_name.replace(' ', '_')):
                success_count += 1

    # 總結
    print(f"\n{'='*80}")
    print(f"匯出完成")
    print(f"{'='*80}")
    print(f"成功: {success_count}/{total_count}")
    print(f"輸出目錄: exports/henry_paul_traintest/")
    print(f"{'='*80}")

    # 列出生成的檔案
    print(f"\n生成的檔案:")
    excel_files = sorted([f for f in os.listdir('exports/henry_paul_traintest') if f.endswith('.xlsx')])
    for f in excel_files:
        size = os.path.getsize(f'exports/henry_paul_traintest/{f}') / 1024
        print(f"  {f:40s} ({size:.1f} KB)")

    print(f"\n{'='*80}")
    print("注意事項:")
    print("  • 每個 Excel 包含兩個 sheet: Training_Data 和 Test_Data")
    print("  • 只包含 11 個特徵（無 class）")
    print("  • Train/Test 使用相同的 StandardScaler（從 Train fit）")
    print("  • like_number, comment_number, view_number 已標準化")
    print("  • Stratified split 保持 class 比例一致")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
