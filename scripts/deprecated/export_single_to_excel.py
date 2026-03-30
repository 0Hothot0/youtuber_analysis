#!/usr/bin/env python3
"""
將 single 數據庫導出為 Excel，並進行 train/test 分割
"""

import sqlite3
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

# 配置
DATABASES = [
    'youtube_analysis_2years_single.db',
    'youtube_analysis_3months_single.db'
]

TEST_SIZE = 0.2  # 20% 作為測試集
RANDOM_STATE = 42  # 固定隨機種子以確保可重現


def export_database_to_excel(db_path: str):
    """導出單個數據庫到 Excel（含 train/test 分割）"""

    if not Path(db_path).exists():
        print(f"❌ 數據庫不存在: {db_path}")
        return False

    print(f"\n{'='*60}")
    print(f"處理: {db_path}")
    print(f"{'='*60}")

    # 讀取數據
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM Youtuber_Financial_Data", conn)
    conn.close()

    print(f"✓ 讀取 {len(df)} 條記錄，{len(df.columns)} 個字段")

    # 檢查是否有 class 字段用於分層抽樣
    if 'class' in df.columns and df['class'].notna().sum() > 0:
        print(f"✓ 使用 'class' 字段進行分層抽樣")
        # 過濾掉 class 為 NULL 的記錄
        df_valid = df[df['class'].notna()].copy()
        df_null = df[df['class'].isna()].copy()

        if len(df_valid) > 0:
            # 分層抽樣
            train_df, test_df = train_test_split(
                df_valid,
                test_size=TEST_SIZE,
                random_state=RANDOM_STATE,
                stratify=df_valid['class']
            )

            print(f"  有效記錄: {len(df_valid)} 條")
            print(f"  NULL 記錄: {len(df_null)} 條 (不參與分割)")
        else:
            print("⚠️  所有記錄的 class 都是 NULL，使用隨機分割")
            train_df, test_df = train_test_split(
                df,
                test_size=TEST_SIZE,
                random_state=RANDOM_STATE
            )
            df_null = pd.DataFrame()
    else:
        print(f"✓ 使用隨機分割")
        train_df, test_df = train_test_split(
            df,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE
        )
        df_null = pd.DataFrame()

    print(f"\n數據分割:")
    print(f"  訓練集: {len(train_df)} 條 ({len(train_df)/len(df)*100:.1f}%)")
    print(f"  測試集: {len(test_df)} 條 ({len(test_df)/len(df)*100:.1f}%)")
    if len(df_null) > 0:
        print(f"  NULL 集: {len(df_null)} 條 (未分類)")

    # 輸出文件名
    base_name = Path(db_path).stem  # 去掉 .db 後綴
    output_dir = Path('exports')
    output_dir.mkdir(exist_ok=True)

    excel_file = output_dir / f"{base_name}.xlsx"

    # 寫入 Excel（多個 sheet）
    print(f"\n寫入 Excel: {excel_file}")
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # 完整數據
        df.to_excel(writer, sheet_name='All_Data', index=False)
        print(f"  ✓ Sheet 'All_Data': {len(df)} 條")

        # 訓練集
        train_df.to_excel(writer, sheet_name='Train', index=False)
        print(f"  ✓ Sheet 'Train': {len(train_df)} 條")

        # 測試集
        test_df.to_excel(writer, sheet_name='Test', index=False)
        print(f"  ✓ Sheet 'Test': {len(test_df)} 條")

        # NULL 集（如果有）
        if len(df_null) > 0:
            df_null.to_excel(writer, sheet_name='Null_Class', index=False)
            print(f"  ✓ Sheet 'Null_Class': {len(df_null)} 條")

        # 統計信息
        stats_data = {
            'Metric': ['Total Records', 'Train Records', 'Test Records', 'Null Records',
                      'Train %', 'Test %', 'Total Columns', 'Random State'],
            'Value': [len(df), len(train_df), len(test_df), len(df_null),
                     f"{len(train_df)/len(df)*100:.1f}%",
                     f"{len(test_df)/len(df)*100:.1f}%",
                     len(df.columns), RANDOM_STATE]
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Statistics', index=False)
        print(f"  ✓ Sheet 'Statistics': 統計信息")

    print(f"\n✅ 成功導出: {excel_file}")
    print(f"   文件大小: {excel_file.stat().st_size / 1024:.1f} KB")

    return True


def main():
    """主程序"""
    print("📊 Single Database Excel 導出工具")
    print(f"{'='*60}")
    print(f"Train/Test 比例: {(1-TEST_SIZE)*100:.0f}% / {TEST_SIZE*100:.0f}%")
    print(f"隨機種子: {RANDOM_STATE}")
    print(f"{'='*60}")

    success_count = 0

    for db_path in DATABASES:
        if export_database_to_excel(db_path):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"📊 導出完成")
    print(f"{'='*60}")
    print(f"成功: {success_count}/{len(DATABASES)} 個數據庫")
    print(f"輸出目錄: exports/")

    if success_count == len(DATABASES):
        print("\n🎉 所有數據庫導出成功!")
        return 0
    else:
        print("\n⚠️  部分數據庫導出失敗")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
