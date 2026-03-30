#!/usr/bin/env python3
"""
匯出 Invest with Henry 和 Paul Thomas 到 Excel（11 個特徵 + 時間序列切分）
使用時間序列切分：早期 80% 為 Train，晚期 20% 為 Test
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

    # 需要 published_time 來做時間切分
    if 'published_time' not in available_columns:
        print(f"  ✗ 缺少 published_time 欄位")
        conn.close()
        return False

    existing_columns = [col for col in SELECTED_COLUMNS if col in available_columns]
    missing_columns = [col for col in SELECTED_COLUMNS if col not in available_columns]

    if missing_columns:
        print(f"  ⚠️  缺少欄位: {', '.join(missing_columns)}")

    # 讀取資料（包含 published_time 用於排序）
    columns_with_time = existing_columns + ['published_time']
    query = f"SELECT {', '.join(columns_with_time)} FROM Youtuber_Financial_Data ORDER BY published_time"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # 轉換時間
    df['published_time'] = pd.to_datetime(df['published_time'])

    print(f"  記錄數: {len(df)}")
    print(f"  特徵數: {len(existing_columns)}")
    print(f"  時間範圍: {df['published_time'].min().date()} 到 {df['published_time'].max().date()}")

    # 時間序列切分：前 80% 為 Train，後 20% 為 Test
    split_idx = int(len(df) * 0.8)

    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    # 顯示切分點
    split_date = train_df['published_time'].max().date()

    print(f"\n  時間序列切分:")
    print(f"    Train: {len(train_df)} 筆 ({train_df['published_time'].min().date()} ~ {train_df['published_time'].max().date()})")
    print(f"    Test:  {len(test_df)} 筆 ({test_df['published_time'].min().date()} ~ {test_df['published_time'].max().date()})")
    print(f"    切分點: {split_date}")
    print(f"    ✓ 無時間重疊")

    # 移除 published_time 欄位
    train_features = train_df[existing_columns]
    test_features = test_df[existing_columns]

    # 打亂順序（在各自的集合內）
    train_features = train_features.sample(frac=1, random_state=42).reset_index(drop=True)
    test_features = test_features.sample(frac=1, random_state=42).reset_index(drop=True)

    # 標準化（使用 train set 的統計數據）
    existing_std_cols = [col for col in COLUMNS_TO_STANDARDIZE if col in train_features.columns]
    print(f"\n  標準化欄位: {', '.join(existing_std_cols)}")

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
    print("11 個特徵 + 時間序列切分（無重疊）")
    print("="*80)
    print(f"\n選擇的特徵:")
    for i, col in enumerate(SELECTED_COLUMNS, 1):
        print(f"  {i:2d}. {col}")
    print(f"\n標準化欄位: {', '.join(COLUMNS_TO_STANDARDIZE)}")
    print(f"切分方式: Time Series Split (80/20)")
    print(f"  • Train: 早期 80% 的數據（按時間排序）")
    print(f"  • Test: 晚期 20% 的數據（按時間排序）")
    print(f"  • 無時間重疊，符合真實預測場景")
    print(f"Random seed: 42 (用於打亂各自集合內的順序)")
    print("="*80)

    # 創建輸出目錄
    os.makedirs('exports/henry_paul_timeseries', exist_ok=True)

    success_count = 0
    total_count = 0

    for youtuber_name, databases in DATABASES.items():
        print(f"\n\n{'='*80}")
        print(f"{youtuber_name}")
        print(f"{'='*80}")

        for db_path, output_name in databases:
            total_count += 1
            output_file = f'exports/henry_paul_timeseries/{output_name}.xlsx'

            if export_database(db_path, output_file, youtuber_name.replace(' ', '_')):
                success_count += 1

    # 總結
    print(f"\n{'='*80}")
    print(f"匯出完成")
    print(f"{'='*80}")
    print(f"成功: {success_count}/{total_count}")
    print(f"輸出目錄: exports/henry_paul_timeseries/")
    print(f"{'='*80}")

    # 列出生成的檔案
    print(f"\n生成的檔案:")
    excel_files = sorted([f for f in os.listdir('exports/henry_paul_timeseries') if f.endswith('.xlsx')])
    for f in excel_files:
        size = os.path.getsize(f'exports/henry_paul_timeseries/{f}') / 1024
        print(f"  {f:40s} ({size:.1f} KB)")

    print(f"\n{'='*80}")
    print("注意事項:")
    print("  • 使用時間序列切分（Train = 早期，Test = 晚期）")
    print("  • Train 和 Test 無時間重疊")
    print("  • 符合真實場景：用過去預測未來")
    print("  • 每個集合內已打亂順序")
    print("  • Train/Test 使用相同的 StandardScaler")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
