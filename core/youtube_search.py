#!/usr/bin/env python3
"""
YouTube 影片搜尋腳本
使用 YouTube Data API v3 根據關鍵字搜尋影片並輸出詳細資訊
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import isodate
import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv
from .db_manager import DatabaseManager


class YouTubeSearcher:
    """YouTube 影片搜尋類別"""

    def __init__(self, api_key):
        """初始化 YouTube API 客戶端"""
        if not api_key:
            raise ValueError("❌ 錯誤：未提供 YouTube API Key")

        try:
            self.youtube = build('youtube', 'v3', developerKey=api_key)
            print("✓ YouTube API 客戶端初始化成功")
        except Exception as e:
            raise Exception(f"❌ YouTube API 初始化失敗: {str(e)}")

    def search_videos(self, keyword, max_results=10, min_age_years=2):
        """
        搜尋影片

        Args:
            keyword: 搜尋關鍵字
            max_results: 最大結果數量（預設 10）
            min_age_years: 最小影片年齡（預設 2 年）

        Returns:
            list: 影片 ID 列表
        """
        try:
            print(f"\n🔍 搜尋關鍵字: '{keyword}'")

            # 計算過濾日期（N 年前）
            cutoff_date = datetime.now() - timedelta(days=min_age_years*365)
            published_before = cutoff_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            print(f"📅 過濾條件: 只搜尋 {cutoff_date.strftime('%Y-%m-%d')} 之前發布的影片")

            # 使用 search.list API 搜尋影片
            search_response = self.youtube.search().list(
                q=keyword,
                type='video',
                part='id,snippet',
                maxResults=max_results,
                order='relevance',  # 按相關性排序
                publishedBefore=published_before  # 只搜尋指定日期之前的影片
            ).execute()

            video_ids = []
            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                video_ids.append(video_id)

            print(f"✓ 找到 {len(video_ids)} 個影片")
            return video_ids

        except Exception as e:
            print(f"❌ 搜尋影片時發生錯誤: {str(e)}")
            return []

    def get_video_details(self, video_ids):
        """
        取得影片詳細資訊

        Args:
            video_ids: 影片 ID 列表

        Returns:
            list: 影片詳細資訊列表
        """
        if not video_ids:
            return []

        try:
            print("\n📊 取得影片詳細資訊...")

            # 使用 videos.list API 取得影片詳細資訊
            videos_response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute()

            videos_data = []

            for item in videos_response.get('items', []):
                video_id = item['id']
                snippet = item['snippet']
                statistics = item.get('statistics', {})
                content_details = item['contentDetails']

                # 解析影片長度
                duration_iso = content_details['duration']
                duration = isodate.parse_duration(duration_iso)
                duration_str = str(duration)

                # 格式化發布日期
                published_at = snippet['publishedAt']
                published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))

                video_info = {
                    'video_id': video_id,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'title': snippet['title'],
                    'channel_name': snippet['channelTitle'],
                    'channel_id': snippet['channelId'],
                    'description': snippet['description'],
                    'published_at': published_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'view_count': int(statistics.get('viewCount', 0)),
                    'like_count': int(statistics.get('likeCount', 0)),
                    'comment_count': int(statistics.get('commentCount', 0)),
                    'duration': duration_str,
                    'thumbnail_default': snippet['thumbnails']['default']['url'],
                    'thumbnail_medium': snippet['thumbnails']['medium']['url'],
                    'thumbnail_high': snippet['thumbnails']['high']['url'],
                }

                videos_data.append(video_info)
                print(f"  ✓ {video_info['title'][:50]}...")

            print(f"\n✓ 成功取得 {len(videos_data)} 個影片的詳細資訊")
            return videos_data

        except Exception as e:
            print(f"❌ 取得影片詳細資訊時發生錯誤: {str(e)}")
            return []

    def get_video_comments(self, video_id, max_comments=None):
        """
        使用分頁抓取影片的所有留言

        Args:
            video_id: YouTube 影片 ID
            max_comments: 最大留言數（None = 全部）

        Returns:
            str: 合併的留言文字，或 None（留言被關閉）
        """
        try:
            all_comments = []
            next_page_token = None

            while True:
                request_params = {
                    'part': 'snippet',
                    'videoId': video_id,
                    'maxResults': 100,
                    'textFormat': 'plainText',
                    'order': 'relevance'
                }

                if next_page_token:
                    request_params['pageToken'] = next_page_token

                response = self.youtube.commentThreads().list(**request_params).execute()

                for item in response.get('items', []):
                    comment_text = item['snippet']['topLevelComment']['snippet']['textDisplay']
                    all_comments.append(comment_text)

                    if max_comments and len(all_comments) >= max_comments:
                        break

                next_page_token = response.get('nextPageToken')
                if not next_page_token or (max_comments and len(all_comments) >= max_comments):
                    break

            return "\n".join(all_comments) if all_comments else ""

        except Exception as e:
            error_str = str(e)
            if 'commentsDisabled' in error_str or '403' in error_str:
                return None  # 留言被關閉
            print(f"  Error fetching comments: {e}")
            return None

    def save_results(self, videos_data, keyword):
        """
        儲存搜尋結果

        Args:
            videos_data: 影片資訊列表
            keyword: 搜尋關鍵字
        """
        if not videos_data:
            print("⚠️ 沒有資料可以儲存")
            return

        # 建立輸出目錄
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)

        # 生成檔案名稱（使用時間戳記）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_keyword = safe_keyword.replace(' ', '_')

        # 儲存 JSON 檔案
        json_filename = output_dir / f'{safe_keyword}_{timestamp}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(videos_data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ JSON 檔案已儲存: {json_filename}")

        # 儲存 CSV 檔案
        csv_filename = output_dir / f'{safe_keyword}_{timestamp}.csv'
        df = pd.DataFrame(videos_data)

        # 調整欄位順序
        columns_order = [
            'video_id', 'title', 'url', 'channel_name', 'channel_id',
            'view_count', 'like_count', 'comment_count',
            'published_at', 'duration',
            'thumbnail_high', 'thumbnail_medium', 'thumbnail_default',
            'description'
        ]
        df = df[columns_order]

        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"✓ CSV 檔案已儲存: {csv_filename}")

        # 顯示摘要
        print(f"\n{'='*60}")
        print(f"搜尋摘要")
        print(f"{'='*60}")
        print(f"關鍵字: {keyword}")
        print(f"影片數量: {len(videos_data)}")
        print(f"總觀看次數: {sum(v['view_count'] for v in videos_data):,}")
        print(f"總按讚數: {sum(v['like_count'] for v in videos_data):,}")
        print(f"{'='*60}\n")

    def save_to_database(self, videos_data, keyword, youtuber_name=None):
        """
        儲存搜尋結果至資料庫

        Args:
            videos_data: 影片資訊列表
            keyword: 搜尋關鍵字
            youtuber_name: YouTuber 名稱 (可選)
        """
        if not videos_data:
            print("⚠️ 沒有資料可以儲存")
            return

        print("\n💾 儲存至資料庫...")

        db = DatabaseManager()
        db.connect()

        # 如果有指定 YouTuber，取得其 ID
        youtuber_id = None
        if youtuber_name:
            # 查詢資料庫中的 YouTuber
            youtubers = db.get_all_youtubers()
            for yt in youtubers:
                if yt['name'].lower() == youtuber_name.lower():
                    youtuber_id = yt['id']
                    print(f"✓ 找到 YouTuber: {yt['name']} (ID: {youtuber_id})")
                    break

            if not youtuber_id:
                print(f"⚠️ 警告：資料庫中找不到 YouTuber '{youtuber_name}'")
                print("   影片將不會關聯到特定 YouTuber")

        # 儲存每個影片
        success_count = 0
        skip_count = 0

        for video in videos_data:
            # 添加額外欄位
            video['search_keyword'] = keyword
            video['youtuber_id'] = youtuber_id

            # 嘗試儲存
            result = db.insert_video(video)
            if result:
                success_count += 1
            else:
                skip_count += 1

        print(f"\n{'='*60}")
        print(f"資料庫儲存結果:")
        print(f"  成功: {success_count} 個影片")
        if skip_count > 0:
            print(f"  略過: {skip_count} 個影片 (已存在)")
        print(f"{'='*60}")

        # 顯示資料庫統計
        stats = db.get_statistics()
        print(f"\n資料庫統計:")
        print(f"  總影片數: {stats['videos']}")
        print(f"  YouTubers: {stats['youtubers']}")
        print(f"  Tags: {stats['tags']}")
        print()

        db.close()


def main():
    """主程式"""
    # 載入環境變數
    load_dotenv()

    # 建立命令列解析器
    parser = argparse.ArgumentParser(
        description='YouTube 影片搜尋工具 - 搜尋影片並儲存至 JSON/CSV/Database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
範例:
  # 基本搜尋（只儲存 JSON/CSV）
  python youtube_search.py "stock market analysis"

  # 搜尋並儲存至資料庫
  python youtube_search.py "stock analysis" --save-db

  # 指定 YouTuber 並儲存至資料庫
  python youtube_search.py "tesla stock" --save-db --youtuber "Invest with Henry"

  # 搜尋更多結果
  python youtube_search.py "AI stocks" --save-db --max-results 20
        '''
    )
    parser.add_argument('keyword', nargs='+', help='搜尋關鍵字')
    parser.add_argument('--save-db', action='store_true', help='儲存結果至資料庫')
    parser.add_argument('--youtuber', type=str, help='指定 YouTuber 名稱（用於資料庫關聯）')
    parser.add_argument('--max-results', type=int, default=10, help='最大結果數量（預設 10）')
    parser.add_argument('--min-age', type=int, default=2, help='最小影片年齡（單位：年，預設 2 年）')

    args = parser.parse_args()

    # 顯示標題
    print("\n" + "="*60)
    print("YouTube 影片搜尋工具")
    print("="*60)

    # 取得 API Key
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        print("\n❌ 錯誤：未設定 YouTube API Key")
        print("\n請執行以下步驟:")
        print("1. 複製 .env.example 為 .env")
        print("   cp .env.example .env")
        print("2. 編輯 .env 檔案，填入你的 API Key")
        print("3. 如何取得 API Key：")
        print("   https://console.cloud.google.com/")
        sys.exit(1)

    keyword = ' '.join(args.keyword)

    try:
        # 初始化搜尋器
        searcher = YouTubeSearcher(api_key)

        # 搜尋影片
        video_ids = searcher.search_videos(keyword, max_results=args.max_results, min_age_years=args.min_age)

        if not video_ids:
            print("\n⚠️ 未找到任何影片")
            sys.exit(0)

        # 取得影片詳細資訊
        videos_data = searcher.get_video_details(video_ids)

        # 儲存結果至 JSON/CSV
        searcher.save_results(videos_data, keyword)

        # 如果指定 --save-db，儲存至資料庫
        if args.save_db:
            searcher.save_to_database(videos_data, keyword, args.youtuber)

        print("✓ 完成！\n")

    except Exception as e:
        print(f"\n❌ 發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
