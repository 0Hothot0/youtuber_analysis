#!/usr/bin/env python3
"""
監控 Gemini 分析進度
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager

def monitor_progress(duration_seconds=300, check_interval=30):
    """
    監控分析進度

    Args:
        duration_seconds: 監控持續時間（秒）
        check_interval: 檢查間隔（秒）
    """
    start_time = time.time()
    last_count = 0

    print("\n" + "="*80)
    print("Gemini 影片分析進度監控")
    print("="*80)

    while time.time() - start_time < duration_seconds:
        db = DatabaseManager()
        db.connect()

        # 獲取統計數據
        db.cursor.execute('SELECT COUNT(*) as count FROM videos')
        total_videos = db.cursor.fetchone()['count']

        db.cursor.execute('SELECT COUNT(*) as count FROM Youtuber_Financial_Data')
        analyzed_videos = db.cursor.fetchone()['count']

        remaining = total_videos - analyzed_videos
        progress_pct = (analyzed_videos / total_videos * 100) if total_videos > 0 else 0

        # 計算速度
        if last_count > 0:
            videos_per_interval = analyzed_videos - last_count
            videos_per_minute = (videos_per_interval / check_interval) * 60
            estimated_minutes = remaining / videos_per_minute if videos_per_minute > 0 else 0
        else:
            videos_per_minute = 0
            estimated_minutes = 0

        last_count = analyzed_videos

        # 顯示進度
        elapsed = int(time.time() - start_time)
        print(f"\n[{elapsed}s] 進度: {analyzed_videos}/{total_videos} ({progress_pct:.1f}%)")
        print(f"  剩餘: {remaining} 個影片")
        if videos_per_minute > 0:
            print(f"  速度: {videos_per_minute:.1f} 影片/分鐘")
            print(f"  預估剩餘時間: {estimated_minutes:.1f} 分鐘")

        # 進度條
        bar_length = 50
        filled = int(bar_length * progress_pct / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"  [{bar}]")

        db.close()

        # 如果完成則退出
        if remaining == 0:
            print("\n✓ 所有影片分析完成！")
            break

        time.sleep(check_interval)

    print("\n" + "="*80)
    print("監控結束")
    print("="*80 + "\n")


if __name__ == '__main__':
    import sys

    # 預設監控 5 分鐘，每 30 秒檢查一次
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    monitor_progress(duration, interval)
