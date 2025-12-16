#!/usr/bin/env python3
"""
資料匯入腳本
讀取 youtuber.txt 並匯入至 SQLite 資料庫與 CSV 檔案
"""

import csv
from pathlib import Path
from db_manager import DatabaseManager


def read_youtuber_file(file_path: str = "youtuber.txt"):
    """
    讀取 youtuber.txt 檔案

    Returns:
        tuple: (youtuber_names, tags)
               youtuber_names: 前 10 行的 YouTuber 名稱列表
               tags: 最後一行的標籤列表
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if len(lines) < 2:
        raise ValueError("youtuber.txt 檔案格式不正確")

    # 前 10 行是 YouTuber 名稱
    youtuber_names = lines[:10]

    # 最後一行是標籤，用逗號分隔
    tags_line = lines[-1]
    tags = [tag.strip() for tag in tags_line.split(',')]

    return youtuber_names, tags


def export_youtubers_to_csv(youtubers, output_path: str = "data/youtubers.csv"):
    """匯出 YouTuber 列表到 CSV"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name'])  # 標題行

        for idx, name in enumerate(youtubers, start=1):
            writer.writerow([idx, name])

    print(f"✓ YouTuber 列表已匯出: {output_path}")


def export_tags_to_csv(tags, output_path: str = "data/search_tags.csv"):
    """匯出搜尋標籤到 CSV"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'tag'])  # 標題行

        for idx, tag in enumerate(tags, start=1):
            writer.writerow([idx, tag])

    print(f"✓ 搜尋標籤已匯出: {output_path}")


def import_to_database(youtubers, tags, db_path: str = "youtube_analysis.db"):
    """匯入資料至 SQLite 資料庫"""
    db = DatabaseManager(db_path)
    db.connect()

    # 建立資料表
    db.create_tables()

    # 匯入 YouTuber
    print("匯入 YouTuber...")
    youtuber_ids = []
    for name in youtubers:
        youtuber_id = db.insert_youtuber(name)
        youtuber_ids.append(youtuber_id)
        print(f"  ✓ {name} (ID: {youtuber_id})")

    # 匯入標籤
    print("\n匯入搜尋標籤...")
    tag_ids = []
    for tag in tags:
        tag_id = db.insert_tag(tag)
        tag_ids.append(tag_id)
        print(f"  ✓ {tag} (ID: {tag_id})")

    # 顯示統計
    print("\n" + "="*60)
    stats = db.get_statistics()
    print("資料庫統計:")
    print(f"  YouTubers: {stats['youtubers']}")
    print(f"  Tags: {stats['tags']}")
    print(f"  Videos: {stats['videos']}")
    print(f"  Financial Data: {stats['financial_data']}")
    print("="*60)

    db.close()


def main():
    """主程式"""
    print("\n" + "="*60)
    print("YouTube 資料匯入工具")
    print("="*60 + "\n")

    try:
        # 讀取 youtuber.txt
        print("讀取 youtuber.txt...")
        youtubers, tags = read_youtuber_file()
        print(f"✓ 讀取到 {len(youtubers)} 個 YouTuber")
        print(f"✓ 讀取到 {len(tags)} 個搜尋標籤\n")

        # 匯出至 CSV
        print("匯出至 CSV...")
        export_youtubers_to_csv(youtubers)
        export_tags_to_csv(tags)
        print()

        # 匯入至資料庫
        print("匯入至 SQLite 資料庫...")
        import_to_database(youtubers, tags)

        print("\n✓ 資料匯入完成！\n")

    except FileNotFoundError:
        print("❌ 錯誤：找不到 youtuber.txt 檔案")
        print("請確認檔案存在於當前目錄")
    except Exception as e:
        print(f"❌ 發生錯誤: {str(e)}")


if __name__ == '__main__':
    main()
