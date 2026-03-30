#!/usr/bin/env python3
"""
為所有 YouTuber 創建時間序列切分的 Excel（11 個特徵）
包括: Joseph, Tom Nash, Fin Tek, Henry, Paul Thomas
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

# 所有 YouTuber 的數據庫
ALL_DATABASES = {
    'Joseph Hogue': [
        ('youtube_analysis_1year_single_joseph.db', 'joseph_1year'),
        ('youtube_analysis_2years_single_joseph.db', 'joseph_2years'),
    ],
    'Tom Nash': [
        ('tom_nash/youtube_analysis_1year_single_tomnash.db', 'tomnash_1year'),
        ('tom_nash/youtube_analysis_2years_single_tomnash.db', 'tomnash_2years'),
    ],
    'Fin Tek': [
        ('fin_tek/youtube_analysis_1year_single_fintek.db', 'fintek_1year'),
        ('fin_tek/youtube_analysis_2years_single_fintek.db', 'fintek_2years'),
    ],
    'Invest with Henry': [
        ('invest_with_henry/youtube_analysis_1year_single_henry.db', 'henry_1year'),
        ('invest_with_henry/youtube_analysis_2years_single_henry.db', 'henry_2years'),
    ],
    'Paul Thomas': [
        ('paul_thomas/youtube_analysis_1year_single_paul.db', 'paul_1year'),
        ('paul_thomas/youtube_analysis_2years_single_paul.db', 'paul_2years'),
    ],
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
    """匯出單一資料庫（時間序列切分）"""
    print(f"\n處理: {db_path}")

    if not os.path.exists(db_path):
        print(f"  ✗ 資料庫不存在")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 檢查哪些欄位存在
    cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
    available_columns = [col[1] for col in cursor.fetchall()]

    if 'published_time' not in available_columns:
        print(f"  ✗ 缺少 published_time 欄位")
        conn.close()
        return False

    existing_columns = [col for col in SELECTED_COLUMNS if col in available_columns]
    missing_columns = [col for col in SELECTED_COLUMNS if col not in available_columns]

    if missing_columns:
        print(f"  ⚠️  缺少欄位: {', '.join(missing_columns)}")

    # 讀取資料（按時間排序）
    columns_with_time = existing_columns + ['published_time']
    query = f"SELECT {', '.join(columns_with_time)} FROM Youtuber_Financial_Data ORDER BY published_time"
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['published_time'] = pd.to_datetime(df['published_time'])

    print(f"  記錄數: {len(df)}")
    print(f"  時間範圍: {df['published_time'].min().date()} 到 {df['published_time'].max().date()}")

    # 時間序列切分：前 80% 為 Train，後 20% 為 Test
    split_idx = int(len(df) * 0.8)

    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    print(f"\n  時間序列切分:")
    print(f"    Train: {len(train_df)} 筆 ({train_df['published_time'].min().date()} ~ {train_df['published_time'].max().date()})")
    print(f"    Test:  {len(test_df)} 筆 ({test_df['published_time'].min().date()} ~ {test_df['published_time'].max().date()})")
    print(f"    ✓ 時間序列切分（早期→晚期）")

    # 移除 published_time
    train_features = train_df[existing_columns]
    test_features = test_df[existing_columns]

    # 打亂順序
    train_features = train_features.sample(frac=1, random_state=42).reset_index(drop=True)
    test_features = test_features.sample(frac=1, random_state=42).reset_index(drop=True)

    # 標準化
    existing_std_cols = [col for col in COLUMNS_TO_STANDARDIZE if col in train_features.columns]
    train_std, scaler = standardize_columns(train_features, COLUMNS_TO_STANDARDIZE, fit=True)
    test_std, _ = standardize_columns(test_features, COLUMNS_TO_STANDARDIZE, scaler=scaler, fit=False)

    # 匯出
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        train_std.to_excel(writer, sheet_name='Training_Data', index=False)
        test_std.to_excel(writer, sheet_name='Test_Data', index=False)

    print(f"  ✓ {output_file}")
    return True


def main():
    print("="*80)
    print("為所有 YouTuber 創建時間序列切分 Excel")
    print("="*80)
    print(f"\n包含 YouTuber:")
    for i, name in enumerate(ALL_DATABASES.keys(), 1):
        print(f"  {i}. {name}")

    print(f"\n特徵數: {len(SELECTED_COLUMNS)}")
    print(f"切分方式: Time Series Split (80/20)")
    print(f"  • Train: 早期 80%")
    print(f"  • Test: 晚期 20%")
    print(f"  • 無時間重疊")
    print("="*80)

    # 創建輸出目錄
    os.makedirs('exports/all_youtubers_timeseries', exist_ok=True)

    success_count = 0
    total_count = 0

    for youtuber_name, databases in ALL_DATABASES.items():
        print(f"\n\n{'='*80}")
        print(f"{youtuber_name}")
        print(f"{'='*80}")

        for db_path, output_name in databases:
            total_count += 1
            output_file = f'exports/all_youtubers_timeseries/{output_name}.xlsx'

            if export_database(db_path, output_file, youtuber_name):
                success_count += 1

    # 總結
    print(f"\n{'='*80}")
    print(f"匯出完成")
    print(f"{'='*80}")
    print(f"成功: {success_count}/{total_count}")
    print(f"輸出目錄: exports/all_youtubers_timeseries/")
    print(f"{'='*80}")

    # 列出生成的檔案
    print(f"\n生成的檔案:")
    excel_files = sorted([f for f in os.listdir('exports/all_youtubers_timeseries') if f.endswith('.xlsx')])

    for youtuber in ['joseph', 'tomnash', 'fintek', 'henry', 'paul']:
        youtuber_files = [f for f in excel_files if f.startswith(youtuber)]
        if youtuber_files:
            print(f"\n  {youtuber.upper()}:")
            for f in youtuber_files:
                size = os.path.getsize(f'exports/all_youtubers_timeseries/{f}') / 1024
                print(f"    {f:40s} ({size:.1f} KB)")

    print(f"\n{'='*80}")
    print("✓ 所有 YouTuber 都使用時間序列切分")
    print("✓ Train 和 Test 無時間重疊")
    print("✓ 符合真實預測場景")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
