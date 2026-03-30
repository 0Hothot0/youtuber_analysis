#!/usr/bin/env python3
"""
Tom Nash 時間序列切分工具
按 during 字段時間序列切分 train/test，然後內部打亂
"""

import sqlite3
import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import StandardScaler

# Tom Nash 的資料庫列表
DATABASES = [
    ('tom_nash/youtube_analysis_2years_single.db', 'tom_nash_2years'),
    ('tom_nash/youtube_analysis_1year_single.db', 'tom_nash_1year'),
    ('tom_nash/youtube_analysis_6months_single.db', 'tom_nash_6months'),
    ('tom_nash/youtube_analysis_3months_single.db', 'tom_nash_3months'),
    ('tom_nash/youtube_analysis_1month_single.db', 'tom_nash_1month'),
]

# 需要標準化的欄位
COLUMNS_TO_STANDARDIZE = ['like_number', 'comment_number', 'view_number', 'during']


def timeseries_split_and_shuffle(df, test_size=0.2, random_state=42):
    """
    時間序列切分後內部打亂

    Args:
        df: DataFrame
        test_size: 測試集比例（預設 0.2 = 20%）
        random_state: 隨機種子

    Returns:
        train_df, test_df: 切分後的 DataFrame
    """
    # 1. 按 during 排序（時間由舊到新）
    df_sorted = df.sort_values('during').reset_index(drop=True)

    # 2. 計算切分點
    split_point = int(len(df_sorted) * (1 - test_size))

    # 3. 切分 train 和 test
    train_df = df_sorted.iloc[:split_point].copy()
    test_df = df_sorted.iloc[split_point:].copy()

    # 4. 在內部打亂（保持時間序列的整體劃分，但避免順序偏差）
    train_df = train_df.sample(frac=1, random_state=random_state).reset_index(drop=True)
    test_df = test_df.sample(frac=1, random_state=random_state).reset_index(drop=True)

    return train_df, test_df


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

    if scaler is None:
        scaler = StandardScaler()

    if fit:
        # Fit 並轉換
        df_copy[columns_to_std] = scaler.fit_transform(df_copy[columns_to_std])
    else:
        # 只轉換（使用已經 fit 的 scaler）
        df_copy[columns_to_std] = scaler.transform(df_copy[columns_to_std])

    return df_copy, scaler


def process_database(db_path, output_prefix):
    """處理單一資料庫"""
    print(f"\n{'='*80}")
    print(f"處理: {db_path}")
    print(f"{'='*80}")

    if not os.path.exists(db_path):
        print(f"  ✗ 資料庫不存在")
        return False

    # 連接資料庫
    conn = sqlite3.connect(db_path)

    # 讀取資料
    query = "SELECT * FROM Youtuber_Financial_Data"
    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"\n原始資料:")
    print(f"  總記錄數: {len(df)}")
    print(f"  唯一影片數: {df['video_id'].nunique()}")

    # 檢查是否有 during 欄位
    if 'during' not in df.columns:
        print(f"  ✗ 缺少 during 欄位，無法進行時間序列切分")
        return False

    # 顯示 during 範圍
    print(f"  during 範圍: {df['during'].min()} - {df['during'].max()} 天")

    # 顯示 class 分佈
    if 'class' in df.columns:
        print(f"\nClass 分佈:")
        class_dist = df['class'].value_counts().sort_index()
        for cls, count in class_dist.items():
            percentage = count / len(df) * 100
            print(f"  Class {cls:2d}: {count:3d} ({percentage:5.1f}%)")

    # 時間序列切分（80/20）
    print(f"\n時間序列切分（按 during 排序後切分）:")
    train_df, test_df = timeseries_split_and_shuffle(df, test_size=0.2, random_state=42)

    print(f"  Train 集: {len(train_df)} ({len(train_df)/len(df)*100:.1f}%)")
    print(f"  Test 集:  {len(test_df)} ({len(test_df)/len(df)*100:.1f}%)")

    # 顯示 during 範圍（驗證時間序列切分）
    print(f"\nTrain 集 during 範圍: {train_df['during'].min()} - {train_df['during'].max()}")
    print(f"Test 集 during 範圍:  {test_df['during'].min()} - {test_df['during'].max()}")

    # 驗證 class 分佈
    if 'class' in df.columns:
        print(f"\nTrain 集 Class 分佈:")
        train_class_dist = train_df['class'].value_counts().sort_index()
        for cls, count in train_class_dist.items():
            percentage = count / len(train_df) * 100
            print(f"  Class {cls:2d}: {count:3d} ({percentage:5.1f}%)")

        print(f"\nTest 集 Class 分佈:")
        test_class_dist = test_df['class'].value_counts().sort_index()
        for cls, count in test_class_dist.items():
            percentage = count / len(test_df) * 100
            print(f"  Class {cls:2d}: {count:3d} ({percentage:5.1f}%)")

    # 標準化欄位（使用 train set 的統計數據）
    print(f"\n標準化欄位: {', '.join(COLUMNS_TO_STANDARDIZE)}")

    # 檢查哪些欄位存在
    existing_cols = [col for col in COLUMNS_TO_STANDARDIZE if col in df.columns]
    if len(existing_cols) < len(COLUMNS_TO_STANDARDIZE):
        missing = set(COLUMNS_TO_STANDARDIZE) - set(existing_cols)
        print(f"  ⚠ 缺少欄位: {missing}，僅標準化: {existing_cols}")

    if existing_cols:
        # 在 train set 上 fit StandardScaler
        train_df_std, scaler = standardize_columns(train_df, existing_cols, fit=True)

        # 在 test set 上使用相同的 scaler（不重新 fit）
        test_df_std, _ = standardize_columns(test_df, existing_cols, scaler=scaler, fit=False)

        # 對 clean 版本也標準化（使用完整資料的統計）
        df_std, _ = standardize_columns(df, existing_cols, fit=True)

        # 顯示標準化統計
        print(f"  標準化後統計（Train）:")
        for col in existing_cols:
            mean = train_df_std[col].mean()
            std = train_df_std[col].std()
            print(f"    {col}: mean={mean:.4f}, std={std:.4f}")
    else:
        # 如果沒有需要標準化的欄位，直接使用原始資料
        train_df_std = train_df
        test_df_std = test_df
        df_std = df

    # 創建輸出目錄
    os.makedirs('exports/tom_nash', exist_ok=True)

    # 匯出 clean 版本（標準化）
    clean_file = f"{output_prefix}_clean.xlsx"
    with pd.ExcelWriter(clean_file, engine='openpyxl') as writer:
        df_std.to_excel(writer, sheet_name='Financial_Data', index=False)
    print(f"\n匯出檔案:")
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
    print("Tom Nash 時間序列切分工具")
    print("="*80)
    print("\n方法:")
    print("  1. 按 during 字段排序（時間由舊到新）")
    print("  2. 前 80% 作為 Train，後 20% 作為 Test")
    print("  3. Train 和 Test 內部分別打亂")
    print("  4. 使用 Train 的統計數據標準化")
    print("="*80)

    success_count = 0

    for db_path, output_name in DATABASES:
        output_prefix = f'exports/tom_nash/{output_name}'

        if process_database(db_path, output_prefix):
            success_count += 1

    # 總結
    print(f"\n{'='*80}")
    print(f"處理完成")
    print(f"{'='*80}")
    print(f"成功: {success_count}/{len(DATABASES)}")
    print(f"輸出目錄: exports/tom_nash/")
    print(f"{'='*80}")

    # 列出生成的檔案
    print(f"\n生成的檔案:")
    if os.path.exists('exports/tom_nash'):
        excel_files = sorted([f for f in os.listdir('exports/tom_nash') if f.endswith('.xlsx')])
        for f in excel_files:
            size = os.path.getsize(f'exports/tom_nash/{f}') / 1024
            print(f"  {f:50s} ({size:.1f} KB)")

    print(f"\n{'='*80}")
    print("注意事項:")
    print("- Train 集的 during 值 < Test 集的 during 值（時間序列保證）")
    print("- Train 和 Test 內部已打亂（避免順序偏差）")
    print("- 使用 Train 集的統計數據標準化 Test 集（避免數據泄漏）")
    print("- 標準化後: mean ≈ 0, std ≈ 1")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
