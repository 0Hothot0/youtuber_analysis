#!/usr/bin/env python3
"""
匯出 Fin Tek 特定欄位到 Excel（帶標準化）
只包含用戶指定的 14 個特徵
"""

import sqlite3
import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Fin Tek 的資料庫列表
DATABASES = [
    ('fin_tek/youtube_analysis_1month_single_fintek.db', 'fintek_1month'),
    ('fin_tek/youtube_analysis_3months_single_fintek.db', 'fintek_3months'),
    ('fin_tek/youtube_analysis_6months_single_fintek.db', 'fintek_6months'),
    ('fin_tek/youtube_analysis_1year_single_fintek.db', 'fintek_1year'),
    ('fin_tek/youtube_analysis_2years_single_fintek.db', 'fintek_2years'),
]

# 用戶指定的欄位
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
    'stock_price_growth_trend',
    'during',
    'class'  # Target variable，放在最後
]

# 需要標準化的欄位
COLUMNS_TO_STANDARDIZE = ['like_number', 'comment_number', 'view_number', 'during']


def standardize_columns(df, columns_to_std, scaler=None, fit=True):
    """
    標準化指定欄位

    Args:
        df: DataFrame
        columns_to_std: 需要標準化的欄位列表
        scaler: StandardScaler 物件（如果已經 fit 過）
        fit: 是否要 fit scaler

    Returns:
        df: 標準化後的 DataFrame
        scaler: 使用的 StandardScaler
    """
    df_copy = df.copy()

    # 只標準化存在的欄位
    existing_cols = [col for col in columns_to_std if col in df_copy.columns]

    if not existing_cols:
        return df_copy, scaler

    if scaler is None:
        scaler = StandardScaler()

    if fit:
        # Fit 並轉換
        df_copy[existing_cols] = scaler.fit_transform(df_copy[existing_cols])
    else:
        # 只轉換（使用已經 fit 的 scaler）
        df_copy[existing_cols] = scaler.transform(df_copy[existing_cols])

    return df_copy, scaler


def export_database(db_path, output_prefix):
    """匯出單一資料庫（只包含指定欄位，帶標準化）"""
    print(f"\n處理: {db_path}")

    if not os.path.exists(db_path):
        print(f"  ✗ 資料庫不存在")
        return False

    # 連接資料庫
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 檢查哪些欄位存在
    cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
    available_columns = [col[1] for col in cursor.fetchall()]

    # 找出實際存在的欄位
    existing_columns = [col for col in SELECTED_COLUMNS if col in available_columns]
    missing_columns = [col for col in SELECTED_COLUMNS if col not in available_columns]

    if missing_columns:
        print(f"  ⚠️  缺少欄位: {', '.join(missing_columns)}")

    print(f"  ✓ 可用欄位: {len(existing_columns)}/{len(SELECTED_COLUMNS)}")

    # 讀取資料（只讀取存在的欄位）
    query = f"SELECT {', '.join(existing_columns)} FROM Youtuber_Financial_Data ORDER BY id"
    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"  記錄數: {len(df)}")
    print(f"  特徵數: {len(df.columns) - 1} (+ class)")

    # 統計
    if 'class' in df.columns:
        class_dist = df['class'].value_counts()
        print(f"  Class 分佈:")
        print(f"    Class 1: {class_dist.get(1, 0)} ({class_dist.get(1, 0)/len(df)*100:.1f}%)")
        print(f"    Class -1: {class_dist.get(-1, 0)} ({class_dist.get(-1, 0)/len(df)*100:.1f}%)")

        # Train/Test 分割（80/20, Stratified）
        train_df, test_df = train_test_split(
            df,
            test_size=0.2,
            random_state=42,
            stratify=df['class']
        )
    else:
        # 如果沒有 class，就隨機分割
        train_df, test_df = train_test_split(
            df,
            test_size=0.2,
            random_state=42
        )

    print(f"  Train: {len(train_df)} 筆")
    print(f"  Test: {len(test_df)} 筆")

    # 標準化欄位（使用 train set 的統計數據）
    existing_std_cols = [col for col in COLUMNS_TO_STANDARDIZE if col in df.columns]
    print(f"  標準化欄位: {', '.join(existing_std_cols)}")

    # 在 train set 上 fit StandardScaler
    train_df_std, scaler = standardize_columns(train_df, COLUMNS_TO_STANDARDIZE, fit=True)

    # 在 test set 上使用相同的 scaler（不重新 fit）
    test_df_std, _ = standardize_columns(test_df, COLUMNS_TO_STANDARDIZE, scaler=scaler, fit=False)

    # 對 clean 版本也標準化（使用完整資料的統計）
    df_std, _ = standardize_columns(df, COLUMNS_TO_STANDARDIZE, fit=True)

    # 顯示標準化統計
    print(f"  標準化後統計（Train）:")
    for col in existing_std_cols:
        mean = train_df_std[col].mean()
        std = train_df_std[col].std()
        print(f"    {col}: mean={mean:.4f}, std={std:.4f}")

    # 匯出 clean 版本（標準化）
    clean_file = f"{output_prefix}_clean.xlsx"
    with pd.ExcelWriter(clean_file, engine='openpyxl') as writer:
        df_std.to_excel(writer, sheet_name='Financial_Data', index=False)
    print(f"  ✓ {clean_file}")

    # 匯出 train 版本（標準化）
    train_file = f"{output_prefix}_train.xlsx"
    with pd.ExcelWriter(train_file, engine='openpyxl') as writer:
        train_df_std.to_excel(writer, sheet_name='Training_Data', index=False)
    print(f"  ✓ {train_file}")

    # 匯出 test 版本（標準化）
    test_file = f"{output_prefix}_test.xlsx"
    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        test_df_std.to_excel(writer, sheet_name='Test_Data', index=False)
    print(f"  ✓ {test_file}")

    return True


def main():
    print("="*80)
    print("Fin Tek 資料庫匯出到 Excel（精簡版 - 14 個特徵）")
    print("="*80)
    print(f"選擇的特徵:")
    for i, col in enumerate(SELECTED_COLUMNS, 1):
        marker = " [Target]" if col == "class" else ""
        print(f"  {i:2d}. {col}{marker}")
    print(f"\n標準化欄位: {', '.join(COLUMNS_TO_STANDARDIZE)}")
    print(f"方法: Z-score normalization (mean=0, std=1)")
    print("="*80)

    # 創建輸出目錄
    os.makedirs('exports/fin_tek_selected', exist_ok=True)

    success_count = 0

    for db_path, output_name in DATABASES:
        output_prefix = f'exports/fin_tek_selected/{output_name}'

        if export_database(db_path, output_prefix):
            success_count += 1

    # 總結
    print(f"\n{'='*80}")
    print(f"匯出完成")
    print(f"{'='*80}")
    print(f"成功: {success_count}/{len(DATABASES)}")
    print(f"輸出目錄: exports/fin_tek_selected/")
    print(f"{'='*80}")

    # 列出生成的檔案
    print(f"\n生成的檔案:")
    excel_files = sorted([f for f in os.listdir('exports/fin_tek_selected') if f.endswith('.xlsx') and not f.startswith('~')])
    for f in excel_files:
        size = os.path.getsize(f'exports/fin_tek_selected/{f}') / 1024
        print(f"  {f:50s} ({size:.1f} KB)")

    print(f"\n{'='*80}")
    print("注意事項:")
    print("- 只包含用戶指定的 14 個欄位（13 個特徵 + 1 個 target）")
    print("- Train/Test 使用相同的 StandardScaler（從 Train set fit）")
    print("- Clean 版本使用完整資料的統計數據標準化")
    print("- 標準化後: mean ≈ 0, std ≈ 1")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
