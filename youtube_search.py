#!/usr/bin/env python3
"""
YouTube 影片搜尋腳本
使用 YouTube Data API v3 根據關鍵字搜尋影片並輸出詳細資訊
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
import isodate
import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv


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

    def search_videos(self, keyword, max_results=10):
        """
        搜尋影片

        Args:
            keyword: 搜尋關鍵字
            max_results: 最大結果數量（預設 10）

        Returns:
            list: 影片 ID 列表
        """
        try:
            print(f"\n🔍 搜尋關鍵字: '{keyword}'")

            # 使用 search.list API 搜尋影片
            search_response = self.youtube.search().list(
                q=keyword,
                type='video',
                part='id,snippet',
                maxResults=max_results,
                order='relevance'  # 按相關性排序
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


def main():
    """主程式"""
    # 載入環境變數
    load_dotenv()

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

    # 取得關鍵字
    if len(sys.argv) < 2:
        print("\n❌ 錯誤：請提供搜尋關鍵字")
        print(f"\n使用方式: python {sys.argv[0]} <關鍵字>")
        print(f"\n範例:")
        print(f"  python {sys.argv[0]} 'stock market analysis'")
        print(f"  python {sys.argv[0]} '台股分析'")
        sys.exit(1)

    keyword = ' '.join(sys.argv[1:])

    try:
        # 初始化搜尋器
        searcher = YouTubeSearcher(api_key)

        # 搜尋影片
        video_ids = searcher.search_videos(keyword, max_results=10)

        if not video_ids:
            print("\n⚠️ 未找到任何影片")
            sys.exit(0)

        # 取得影片詳細資訊
        videos_data = searcher.get_video_details(video_ids)

        # 儲存結果
        searcher.save_results(videos_data, keyword)

        print("✓ 完成！\n")

    except Exception as e:
        print(f"\n❌ 發生錯誤: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
