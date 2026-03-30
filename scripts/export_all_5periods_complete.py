#!/usr/bin/env python3
"""
為所有 YouTuber 創建完整的 5 個時間區間 Excel（時間序列切分）
1個月、3個月、6個月、1年、2年
"""

import sqlite3
import pandas as pd
import os
from sklearn.preprocessing import StandardScaler

# 用戶指定的 13 個特徵（包含 class）
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
    'class',  # 每個時期不同（基於該時期的 return_rate）
]

COLUMNS_TO_STANDARDIZE = ['like_number', 'comment_number', 'view_number']

# 所有 YouTuber 的完整數據庫（5 個時間區間）
ALL_DATABASES = {
    'Joseph': [
        ('joseph/youtube_analysis_1month_single_joseph.db', 'joseph_1month'),
        ('joseph/youtube_analysis_3months_single_joseph.db', 'joseph_3months'),
        ('joseph/youtube_analysis_6months_single_joseph.db', 'joseph_6months'),
        ('joseph/youtube_analysis_1year_single_joseph.db', 'joseph_1year'),
        ('joseph/youtube_analysis_2years_single_joseph.db', 'joseph_2years'),
    ],
    'Tom Nash': [
        ('tom_nash/youtube_analysis_1month_single_tomnash.db', 'tomnash_1month'),
        ('tom_nash/youtube_analysis_3months_single_tomnash.db', 'tomnash_3months'),
        ('tom_nash/youtube_analysis_6months_single_tomnash.db', 'tomnash_6months'),
        ('tom_nash/youtube_analysis_1year_single_tomnash.db', 'tomnash_1year'),
        ('tom_nash/youtube_analysis_2years_single_tomnash.db', 'tomnash_2years'),
    ],
    'Fin Tek': [
        ('fin_tek/youtube_analysis_1month_single_fintek.db', 'fintek_1month'),
        ('fin_tek/youtube_analysis_3months_single_fintek.db', 'fintek_3months'),
        ('fin_tek/youtube_analysis_6months_single_fintek.db', 'fintek_6months'),
        ('fin_tek/youtube_analysis_1year_single_fintek.db', 'fintek_1year'),
        ('fin_tek/youtube_analysis_2years_single_fintek.db', 'fintek_2years'),
    ],
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


def export_database(db_path, output_file):
    """匯出單一資料庫（時間序列切分）"""
    if not os.path.exists(db_path):
        return False, "檔案不存在"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 檢查欄位
        cursor.execute("PRAGMA table_info(Youtuber_Financial_Data)")
        available_columns = [col[1] for col in cursor.fetchall()]

        if 'published_time' not in available_columns:
            conn.close()
            return False, "缺少 published_time"

        existing_columns = [col for col in SELECTED_COLUMNS if col in available_columns]

        # 讀取資料（按時間排序）
        columns_with_time = existing_columns + ['published_time']
        query = f"SELECT {', '.join(columns_with_time)} FROM Youtuber_Financial_Data ORDER BY published_time"
        df = pd.read_sql_query(query, conn)
        conn.close()

        df['published_time'] = pd.to_datetime(df['published_time'])

        # 時間序列切分
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()

        # 移除 published_time
        train_features = train_df[existing_columns]
        test_features = test_df[existing_columns]

        # 打亂順序
        train_features = train_features.sample(frac=1, random_state=42).reset_index(drop=True)
        test_features = test_features.sample(frac=1, random_state=42).reset_index(drop=True)

        # 標準化
        train_std, scaler = standardize_columns(train_features, COLUMNS_TO_STANDARDIZE, fit=True)
        test_std, _ = standardize_columns(test_features, COLUMNS_TO_STANDARDIZE, scaler=scaler, fit=False)

        # 匯出
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            train_std.to_excel(writer, sheet_name='Training_Data', index=False)
            test_std.to_excel(writer, sheet_name='Test_Data', index=False)

        return True, f"{len(train_features)}/{len(test_features)}"

    except Exception as e:
        return False, str(e)


def main():
    print("="*100)
    print("為所有 YouTuber 創建完整 5 個時間區間的 Excel（時間序列切分）")
    print("="*100)

    os.makedirs('exports/all_5periods_timeseries', exist_ok=True)

    results = {}

    for youtuber_name, databases in ALL_DATABASES.items():
        print(f"\n{'='*100}")
        print(f"{youtuber_name}")
        print(f"{'='*100}")

        results[youtuber_name] = {}

        for db_path, output_name in databases:
            output_file = f'exports/all_5periods_timeseries/{output_name}.xlsx'
            period = output_name.split('_')[-1]  # 提取時間區間

            success, info = export_database(db_path, output_file)

            if success:
                print(f"  ✓ {period:10s}: {info:15s} → {output_name}.xlsx")
                results[youtuber_name][period] = '✓'
            else:
                print(f"  ✗ {period:10s}: {info}")
                results[youtuber_name][period] = '✗'

    # 總結表格
    print(f"\n{'='*100}")
    print("完成統計")
    print(f"{'='*100}\n")

    periods = ['1month', '3months', '6months', '1year', '2years']

    print(f"{'YouTuber':20s} {'1月':6s} {'3月':6s} {'6月':6s} {'1年':6s} {'2年':6s} {'完成度':8s}")
    print('-'*100)

    for youtuber, period_results in results.items():
        row = [period_results.get(p, '✗') for p in periods]
        completed = sum(1 for r in row if r == '✓')
        completion = f"{completed}/5"

        name_short = youtuber.split()[0] if ' ' in youtuber else youtuber
        print(f"{name_short:20s} {row[0]:6s} {row[1]:6s} {row[2]:6s} {row[3]:6s} {row[4]:6s} {completion:8s}")

    # 列出所有生成的文件
    print(f"\n{'='*100}")
    print(f"生成的檔案: exports/all_5periods_timeseries/")
    print(f"{'='*100}")

    excel_files = sorted([f for f in os.listdir('exports/all_5periods_timeseries') if f.endswith('.xlsx')])

    for youtuber in ['joseph', 'tomnash', 'fintek', 'henry', 'paul']:
        youtuber_files = [f for f in excel_files if f.startswith(youtuber)]
        if youtuber_files:
            print(f"\n{youtuber.upper()}:")
            for f in youtuber_files:
                size = os.path.getsize(f'exports/all_5periods_timeseries/{f}') / 1024
                print(f"  {f:45s} ({size:5.1f} KB)")

    print(f"\n{'='*100}")
    print("✓ 所有數據使用時間序列切分（Train = 早期 80%, Test = 晚期 20%）")
    print("✓ 無時間重疊，符合真實預測場景")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
