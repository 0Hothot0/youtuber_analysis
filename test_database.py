#!/usr/bin/env python3
"""
測試腳本 - 驗證資料庫內容
"""

from db_manager import DatabaseManager

def main():
    db = DatabaseManager()
    db.connect()

    print("\n" + "="*80)
    print("資料庫內容驗證")
    print("="*80)

    # 統計資訊
    stats = db.get_statistics()
    print("\n【統計資訊】")
    print(f"  YouTubers: {stats['youtubers']}")
    print(f"  Tags: {stats['tags']}")
    print(f"  Videos: {stats['videos']}")
    print(f"  Financial Data: {stats['financial_data']}")

    # 顯示所有 YouTuber
    print("\n【YouTuber 清單】")
    youtubers = db.get_all_youtubers()
    for yt in youtubers:
        print(f"  {yt['id']:2d}. {yt['name']}")

    # 顯示影片統計（按 YouTuber）
    print("\n【影片統計（按 YouTuber）】")
    for yt in youtubers:
        videos = db.get_videos_by_youtuber(yt['id'])
        if videos:
            print(f"  {yt['name']:25s} : {len(videos)} 個影片")

    # 顯示所有影片（簡要資訊）
    print("\n【影片清單】")
    db.cursor.execute("""
        SELECT v.video_id, v.title, v.view_count, v.search_keyword, y.name as youtuber_name
        FROM videos v
        LEFT JOIN youtubers y ON v.youtuber_id = y.id
        ORDER BY v.created_at DESC
    """)
    videos = db.cursor.fetchall()

    for idx, video in enumerate(videos, 1):
        youtuber = video['youtuber_name'] if video['youtuber_name'] else "未指定"
        print(f"\n  [{idx}] {video['title'][:60]}")
        print(f"      Video ID: {video['video_id']}")
        print(f"      觀看次數: {video['view_count']:,}")
        print(f"      搜尋關鍵字: {video['search_keyword']}")
        print(f"      YouTuber: {youtuber}")

    # 顯示搜尋標籤（前 10 個）
    print("\n【搜尋標籤（前 10 個）】")
    tags = db.get_all_tags()[:10]
    for tag in tags:
        print(f"  {tag['id']:2d}. {tag['tag']}")

    print("\n" + "="*80)
    print("驗證完成")
    print("="*80 + "\n")

    db.close()


if __name__ == '__main__':
    main()
