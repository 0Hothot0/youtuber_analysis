#!/usr/bin/env python3
"""
將 Joseph 資料分割成 Train 和 Test 集
支援分層抽樣，保持 class 比例
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import os

def split_and_export(excel_file, test_size=0.2, random_state=42):
    """
    分割資料集並匯出

    Args:
        excel_file: 輸入的 Excel 檔案
        test_size: 測試集比例（預設 0.2 = 20%）
        random_state: 隨機種子（確保可重現）
    """
    print(f"\n{'='*80}")
    print(f"處理: {excel_file}")
    print(f"{'='*80}")

    # 讀取資料
    df = pd.read_excel(excel_file)
    print(f"\n原始資料:")
    print(f"  總記錄數: {len(df)}")
    print(f"  唯一影片數: {df['video_id'].nunique()}")
    print(f"  唯一股票數: {df['stock_ticker'].nunique()}")

    # 顯示 class 分佈
    print(f"\nClass 分佈:")
    class_dist = df['class'].value_counts().sort_index()
    for cls, count in class_dist.items():
        percentage = count / len(df) * 100
        print(f"  Class {cls:2d}: {count:3d} ({percentage:5.1f}%)")

    # 使用分層抽樣（stratified split）保持 class 比例
    train_df, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=df['class']  # 按 class 分層
    )

    print(f"\n分割結果:")
    print(f"  Train 集: {len(train_df)} ({len(train_df)/len(df)*100:.1f}%)")
    print(f"  Test 集:  {len(test_df)} ({len(test_df)/len(df)*100:.1f}%)")

    # 驗證 class 分佈
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

    # 生成輸出檔名
    base_name = excel_file.replace('_clean.xlsx', '')
    train_file = f"{base_name}_train.xlsx"
    test_file = f"{base_name}_test.xlsx"

    # 匯出
    print(f"\n匯出檔案:")

    with pd.ExcelWriter(train_file, engine='openpyxl') as writer:
        train_df.to_excel(writer, sheet_name='Train_Data', index=False)
    print(f"  ✓ {train_file}")

    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        test_df.to_excel(writer, sheet_name='Test_Data', index=False)
    print(f"  ✓ {test_file}")

    # 檔案大小
    train_size = os.path.getsize(train_file) / 1024
    test_size = os.path.getsize(test_file) / 1024
    print(f"\n檔案大小:")
    print(f"  Train: {train_size:.1f} KB")
    print(f"  Test:  {test_size:.1f} KB")

    return train_df, test_df


def main():
    print("="*80)
    print("Joseph 資料集分割工具 (Train/Test Split)")
    print("="*80)
    print("\n設定:")
    print("  分割比例: 80% Train / 20% Test")
    print("  方法: Stratified Split (保持 class 比例)")
    print("  隨機種子: 42 (確保可重現)")

    # Joseph 資料檔案
    files = [
        'joseph_2years_clean.xlsx',
        'joseph_3months_clean.xlsx'
    ]

    all_results = []

    for file in files:
        if not os.path.exists(file):
            print(f"\n⚠ 檔案不存在: {file}")
            continue

        train_df, test_df = split_and_export(file, test_size=0.2, random_state=42)
        all_results.append({
            'file': file,
            'train': train_df,
            'test': test_df
        })

    # 總結
    print(f"\n{'='*80}")
    print("分割完成總結")
    print(f"{'='*80}")

    print("\n生成的檔案:")
    for result in all_results:
        base = result['file'].replace('_clean.xlsx', '')
        print(f"\n📁 {result['file']}:")
        print(f"  → {base}_train.xlsx ({len(result['train'])} 筆)")
        print(f"  → {base}_test.xlsx ({len(result['test'])} 筆)")

    print(f"\n{'='*80}")
    print("✓ 所有檔案已準備就緒！")
    print(f"{'='*80}\n")

    # 顯示使用建議
    print("💡 使用建議:")
    print("  - Train 集用於訓練模型")
    print("  - Test 集用於評估模型效能")
    print("  - Class 比例已保持一致（Stratified Split）")
    print("  - 隨機種子固定，結果可重現")
    print()


if __name__ == "__main__":
    main()
